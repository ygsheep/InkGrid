'use client';

import { useState } from 'react';
import { App, Button, Form, Input, Modal, Popconfirm, Select, Space, Table, Tag, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { Edit3, Plus, Trash2 } from 'lucide-react';
import {
  useAdminPersonas,
  useCreatePersona,
  useDeletePersona,
  useUpdatePersona,
} from '@/hooks/useAdmin';
import type {
  AdminPersona,
  PersonaCreatePayload,
  PersonaUpdatePayload,
} from '@/lib/api/admin';

type FormValues = {
  serial: string;
  name: string;
  tagline: string;
  description: string;
  tags?: string[];
  avatar?: string;
  system_prompt: string;
  scope: string;
};

const SCOPE_OPTIONS = [
  { label: '全局', value: 'global' },
  { label: '频道', value: 'channel' },
  { label: '文章', value: 'article' },
];

function fieldLabel(text: string) {
  return (
    <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
      {text}
    </span>
  );
}

export default function AdminPersonaPage() {
  const { message } = App.useApp();
  const [form] = Form.useForm<FormValues>();
  const [editing, setEditing] = useState<{ open: boolean; persona?: AdminPersona }>({
    open: false,
  });

  const { data, isLoading, isFetching } = useAdminPersonas({ size: 100 });

  const createPersona = useCreatePersona({
    onSuccess: () => {
      message.success('已创建');
      setEditing({ open: false });
      form.resetFields();
    },
    onError: (e) => message.error(e.message),
  });

  const updatePersona = useUpdatePersona({
    onSuccess: () => {
      message.success('已保存');
      setEditing({ open: false });
      form.resetFields();
    },
    onError: (e) => message.error(e.message),
  });

  const deletePersona = useDeletePersona({
    onSuccess: () => message.success('已删除'),
    onError: (e) => message.error(e.message),
  });

  const openNew = () => {
    form.resetFields();
    setEditing({ open: true });
  };

  const openEdit = (p: AdminPersona) => {
    form.setFieldsValue({
      serial: p.serial,
      name: p.name,
      tagline: p.tagline,
      description: p.description,
      tags: p.tags || [],
      avatar: p.avatar || undefined,
      system_prompt: p.system_prompt,
      scope: p.scope,
    });
    setEditing({ open: true, persona: p });
  };

  const onSubmit = (values: FormValues) => {
    const tags = values.tags?.length ? values.tags : null;
    if (editing.persona) {
      const payload: PersonaUpdatePayload = {
        serial: values.serial,
        name: values.name,
        tagline: values.tagline,
        description: values.description,
        tags,
        avatar: values.avatar || null,
        system_prompt: values.system_prompt,
        scope: values.scope,
      };
      updatePersona.mutate({ id: editing.persona.id, payload });
    } else {
      const payload: PersonaCreatePayload = {
        serial: values.serial,
        name: values.name,
        tagline: values.tagline,
        description: values.description,
        tags,
        avatar: values.avatar || null,
        system_prompt: values.system_prompt,
        scope: values.scope,
      };
      createPersona.mutate(payload);
    }
  };

  const columns: ColumnsType<AdminPersona> = [
    {
      title: '序号',
      dataIndex: 'serial',
      key: 'serial',
      width: 80,
      render: (v: string) => (
        <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
          {v}
        </span>
      ),
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (_, r) => (
        <div>
          <span className="text-on-surface">{r.name}</span>
          <div className="text-on-surface-variant text-body-sm mt-0.5">{r.tagline}</div>
        </div>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (v: string) => <span className="text-on-surface-variant">{v}</span>,
    },
    {
      title: 'Scope',
      dataIndex: 'scope',
      key: 'scope',
      width: 100,
      render: (v: string) => (
        <Tag className="font-mono uppercase">{v}</Tag>
      ),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      width: 200,
      render: (tags: string[] | null) =>
        tags && tags.length ? (
          <Space size={4} wrap>
            {tags.map((t) => (
              <Tag key={t} className="font-mono">
                {t}
              </Tag>
            ))}
          </Space>
        ) : (
          <span className="text-tertiary-fixed">—</span>
        ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_, r) => (
        <Space size={0}>
          <Tooltip title="编辑">
            <Button
              type="text"
              size="small"
              icon={<Edit3 size={14} />}
              onClick={() => openEdit(r)}
            />
          </Tooltip>
          <Tooltip title="删除">
            <Popconfirm
              title="删除人设"
              description="关联频道的 persona 将被置空，确定删除？"
              okText="删除"
              cancelText="取消"
              onConfirm={() => deletePersona.mutate(r.id)}
            >
              <Button
                type="text"
                size="small"
                danger
                icon={<Trash2 size={14} />}
                loading={deletePersona.isPending}
              />
            </Popconfirm>
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
            人设配置
          </h1>
          <p className="font-mono text-label-mono text-on-surface-variant mt-2 uppercase tracking-widest">
            PERSONAS · AI 代答口吻 / 语气 / 禁答边界
          </p>
        </div>
        <Button type="primary" icon={<Plus size={14} />} onClick={openNew}>
          新建人设
        </Button>
      </div>

      <Table<AdminPersona>
        rowKey="id"
        columns={columns}
        dataSource={data?.items}
        loading={isLoading || isFetching}
        pagination={false}
        size="middle"
      />

      <Modal
        open={editing.open}
        title={editing.persona ? '编辑人设' : '新建人设'}
        onCancel={() => {
          setEditing({ open: false });
          form.resetFields();
        }}
        okText={editing.persona ? '保存' : '创建'}
        cancelText="取消"
        confirmLoading={createPersona.isPending || updatePersona.isPending}
        onOk={() => form.submit()}
        width={720}
        destroyOnHidden
      >
        <Form<FormValues>
          form={form}
          layout="vertical"
          onFinish={onSubmit}
          requiredMark={false}
          initialValues={{ scope: 'global' }}
        >
          <div className="grid grid-cols-2 gap-3">
            <Form.Item
              name="serial"
              label={fieldLabel('序号')}
              rules={[{ required: true, message: '请输入序号' }]}
            >
              <Input placeholder="如：001" />
            </Form.Item>
            <Form.Item
              name="name"
              label={fieldLabel('名称')}
              rules={[{ required: true, message: '请输入名称' }]}
            >
              <Input placeholder="如：博客作者" />
            </Form.Item>
          </div>

          <Form.Item
            name="tagline"
            label={fieldLabel('Tagline')}
            rules={[{ required: true, message: '请输入 tagline' }]}
          >
            <Input placeholder="如：博主本人" />
          </Form.Item>

          <Form.Item
            name="description"
            label={fieldLabel('描述')}
            rules={[{ required: true, message: '请输入描述' }]}
          >
            <Input.TextArea
              autoSize={{ minRows: 2, maxRows: 4 }}
              placeholder="对外展示的人设介绍"
            />
          </Form.Item>

          <Form.Item
            name="system_prompt"
            label={fieldLabel('System Prompt')}
            rules={[{ required: true, message: '请输入 system prompt' }]}
            extra={
              <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
                LLM 系统提示词，定义口吻/语气/禁答边界
              </span>
            }
          >
            <Input.TextArea
              autoSize={{ minRows: 6, maxRows: 14 }}
              placeholder="你是 XX，回答时保持..."
              className="font-mono"
              style={{ fontFamily: 'var(--font-jetbrains), monospace' }}
            />
          </Form.Item>

          <div className="grid grid-cols-2 gap-3">
            <Form.Item name="scope" label={fieldLabel('Scope')}>
              <Select options={SCOPE_OPTIONS} />
            </Form.Item>
            <Form.Item name="tags" label={fieldLabel('标签')}>
              <Select
                mode="tags"
                placeholder="按回车添加"
                tokenSeparators={[',', ' ']}
              />
            </Form.Item>
          </div>

          <Form.Item name="avatar" label={fieldLabel('头像 URL')}>
            <Input placeholder="可空" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
