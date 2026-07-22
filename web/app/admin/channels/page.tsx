'use client';

import { useState } from 'react';
import { App, Button, Form, Input, Modal, Select, Space, Table, Tag, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { Edit3, Plus, Trash2 } from 'lucide-react';
import {
  useAdminChannels,
  useAdminPersonas,
  useCreateChannel,
  useDeleteChannel,
  useUpdateChannel,
} from '@/hooks/useAdmin';
import type { AdminChannel, ChannelCreatePayload } from '@/lib/api/admin';
import { formatDate } from '@/lib/utils';

type FormValues = {
  slug: string;
  name: string;
  description?: string;
  accent?: string;
  persona_id?: string;
};

const ACCENT_OPTIONS = [
  { label: '默认（白）', value: 'channel' },
  { label: '政策（绿）', value: 'policy' },
];

const ACCENT_LABEL: Record<string, string> = {
  channel: '默认',
  policy: '政策',
};

function fieldLabel(text: string) {
  return (
    <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
      {text}
    </span>
  );
}

export default function AdminChannelsPage() {
  const { message, modal } = App.useApp();
  const [form] = Form.useForm<FormValues>();
  const [editing, setEditing] = useState<{ open: boolean; channel?: AdminChannel }>({
    open: false,
  });

  // 列表 + 人设下拉
  const { data, isLoading, isFetching } = useAdminChannels({ size: 100 });
  const { data: personasData } = useAdminPersonas({ size: 100 });

  const createChannel = useCreateChannel({
    onSuccess: () => {
      message.success('已创建');
      setEditing({ open: false });
      form.resetFields();
    },
    onError: (e) => message.error(e.message),
  });

  const updateChannel = useUpdateChannel({
    onSuccess: () => {
      message.success('已保存');
      setEditing({ open: false });
      form.resetFields();
    },
    onError: (e) => message.error(e.message),
  });

  const deleteChannel = useDeleteChannel({
    onSuccess: () => message.success('已删除'),
    onError: (e) => message.error(e.message),
  });

  const openNew = () => {
    form.resetFields();
    setEditing({ open: true });
  };

  const openEdit = (ch: AdminChannel) => {
    form.setFieldsValue({
      slug: ch.slug,
      name: ch.name,
      description: ch.description || undefined,
      accent: ch.accent || 'channel',
      persona_id: ch.persona_id || undefined,
    });
    setEditing({ open: true, channel: ch });
  };

  const onSubmit = (values: FormValues) => {
    const payload: ChannelCreatePayload = {
      slug: values.slug,
      name: values.name,
      description: values.description || null,
      accent: values.accent || null,
      persona_id: values.persona_id || null,
    };
    if (editing.channel) {
      updateChannel.mutate({ id: editing.channel.id, payload });
    } else {
      createChannel.mutate(payload);
    }
  };

  const columns: ColumnsType<AdminChannel> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (_, r) => (
        <div>
          <span className="text-on-surface">{r.name}</span>
          <div className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest mt-0.5">
            /{r.slug}
          </div>
        </div>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (v: string | null) =>
        v ? (
          <span className="text-on-surface-variant">{v}</span>
        ) : (
          <span className="text-tertiary-fixed">—</span>
        ),
    },
    {
      title: 'Accent',
      dataIndex: 'accent',
      key: 'accent',
      width: 100,
      render: (v: string | null) =>
        v ? (
          <Tag className="font-mono uppercase">{ACCENT_LABEL[v] || v}</Tag>
        ) : (
          <span className="text-tertiary-fixed">—</span>
        ),
    },
    {
      title: '文章数',
      dataIndex: 'postCount',
      key: 'postCount',
      width: 80,
      render: (n: number) => (
        <span className="font-mono text-on-surface-variant tabular-nums">{n}</span>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (v: string | null) =>
        v ? (
          <span className="font-mono text-label-mono text-on-surface-variant tabular-nums">
            {formatDate(v)}
          </span>
        ) : (
          <span className="text-tertiary-fixed">—</span>
        ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 140,
      render: (_, r) => (
        <Space size={4}>
          <Tooltip title="编辑">
            <Button
              type="text"
              size="small"
              icon={<Edit3 size={14} />}
              onClick={() => openEdit(r)}
            />
          </Tooltip>
          <Tooltip title="删除">
            <Button
              type="text"
              size="small"
              danger
              icon={<Trash2 size={14} />}
              onClick={() => {
                modal.confirm({
                  title: '删除频道',
                  content:
                    r.postCount > 0
                      ? `频道下有 ${r.postCount} 篇文章，无法直接删除（外键约束）。请先迁移或删除文章。`
                      : `确定删除「${r.name}」？`,
                  okText: '删除',
                  okButtonProps: { danger: true },
                  cancelText: '取消',
                  onOk: async () => {
                    if (r.postCount > 0) return;
                    await deleteChannel.mutateAsync(r.id);
                  },
                });
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
            频道管理
          </h1>
          <p className="font-mono text-label-mono text-on-surface-variant mt-2 uppercase tracking-widest">
            CHANNELS · 创建 / 编辑 / 删除
          </p>
        </div>
        <Button type="primary" icon={<Plus size={14} />} onClick={openNew}>
          新建频道
        </Button>
      </div>

      <Table<AdminChannel>
        rowKey="id"
        columns={columns}
        dataSource={data?.items}
        loading={isLoading || isFetching}
        pagination={false}
        size="middle"
      />

      <Modal
        open={editing.open}
        title={editing.channel ? '编辑频道' : '新建频道'}
        onCancel={() => {
          setEditing({ open: false });
          form.resetFields();
        }}
        okText={editing.channel ? '保存' : '创建'}
        cancelText="取消"
        confirmLoading={createChannel.isPending || updateChannel.isPending}
        onOk={() => form.submit()}
        destroyOnHidden
      >
        <Form<FormValues>
          form={form}
          layout="vertical"
          onFinish={onSubmit}
          requiredMark={false}
          initialValues={{ accent: 'channel' }}
        >
          <Form.Item
            name="name"
            label={fieldLabel('名称')}
            rules={[{ required: true, message: '请输入名称' }]}
          >
            <Input placeholder="如：个人经验" />
          </Form.Item>
          <Form.Item
            name="slug"
            label={fieldLabel('Slug')}
            rules={[
              { required: true, message: '请输入 slug' },
              {
                pattern: /^[a-z0-9-]+$/,
                message: '只能小写字母/数字/连字符',
              },
            ]}
          >
            <Input placeholder="url-friendly-slug" />
          </Form.Item>
          <Form.Item name="description" label={fieldLabel('描述')}>
            <Input.TextArea autoSize={{ minRows: 2, maxRows: 4 }} placeholder="频道简介" />
          </Form.Item>
          <div className="grid grid-cols-2 gap-3">
            <Form.Item name="accent" label={fieldLabel('Accent')}>
              <Select options={ACCENT_OPTIONS} />
            </Form.Item>
            <Form.Item name="persona_id" label={fieldLabel('人设')}>
              <Select
                allowClear
                placeholder="未绑定"
                options={(personasData?.items || []).map((p) => ({
                  label: `${p.serial} · ${p.name}`,
                  value: p.id,
                }))}
              />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </div>
  );
}
