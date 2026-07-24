'use client';

import { useState } from 'react';
import {
  App,
  Button,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { Check, Edit3, X as XIcon, RefreshCw } from 'lucide-react';
import {
  useAdminQa,
  useReindexQa,
  useReviewQa,
} from '@/hooks/useAdmin';
import type { AdminQaPair, QaReviewPayload } from '@/lib/api/admin';

const STATUS_OPTIONS = [
  { label: '待审核', value: 'pending' },
  { label: '已通过', value: 'approved' },
  { label: '已拒绝', value: 'rejected' },
];

const STATUS_COLOR: Record<string, string> = {
  pending: 'orange',
  approved: 'green',
  rejected: 'red',
};

const STATUS_LABEL: Record<string, string> = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已拒绝',
};

type EditFormValues = {
  question: string;
  answer: string;
};

function fieldLabel(text: string) {
  return (
    <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
      {text}
    </span>
  );
}

export default function AdminQaPage() {
  const { message } = App.useApp();
  const [form] = Form.useForm<EditFormValues>();
  const [statusFilter, setStatusFilter] = useState<string>('pending');
  const [editing, setEditing] = useState<{
    open: boolean;
    qa?: AdminQaPair;
  }>({ open: false });

  const { data, isLoading, isFetching } = useAdminQa({
    status: statusFilter,
    size: 100,
  });

  const reviewQa = useReviewQa({
    onSuccess: () => {
      message.success('已保存');
      setEditing({ open: false });
      form.resetFields();
    },
    onError: (e) => message.error(e.message),
  });

  const reindexQa = useReindexQa({
    onSuccess: () => message.success('已写入向量库'),
    onError: (e) => message.error(e.message),
  });

  const openEdit = (qa: AdminQaPair) => {
    form.setFieldsValue({
      question: qa.question,
      answer: qa.answer,
    });
    setEditing({ open: true, qa });
  };

  const onSubmit = (values: EditFormValues) => {
    if (!editing.qa) return;
    const payload: QaReviewPayload = {
      status: 'approved',
      question: values.question,
      answer: values.answer,
    };
    reviewQa.mutate({ id: editing.qa.id, payload });
  };

  const handleReject = (qa: AdminQaPair) => {
    reviewQa.mutate({
      id: qa.id,
      payload: { status: 'rejected' },
    });
  };

  const handleApprove = (qa: AdminQaPair) => {
    reviewQa.mutate({
      id: qa.id,
      payload: { status: 'approved' },
    });
  };

  const columns: ColumnsType<AdminQaPair> = [
    {
      title: '问题',
      dataIndex: 'question',
      key: 'question',
      ellipsis: true,
      render: (v: string) => (
        <span className="text-on-surface">{v}</span>
      ),
    },
    {
      title: '答案',
      dataIndex: 'answer',
      key: 'answer',
      ellipsis: true,
      render: (v: string) => (
        <span className="text-on-surface-variant text-body-sm">
          {v.length > 80 ? v.slice(0, 80) + '…' : v}
        </span>
      ),
    },
    {
      title: '来源文章',
      dataIndex: 'article_title',
      key: 'article_title',
      width: 180,
      ellipsis: true,
      render: (v: string | null) =>
        v ? (
          <span className="text-on-surface-variant">{v}</span>
        ) : (
          <span className="text-tertiary-fixed">—</span>
        ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (v: string) => (
        <Tag color={STATUS_COLOR[v] || 'default'} className="font-mono uppercase">
          {STATUS_LABEL[v] || v}
        </Tag>
      ),
    },
    {
      title: '入库',
      dataIndex: 'milvus_chunk_id',
      key: 'milvus_chunk_id',
      width: 80,
      render: (v: string | null) =>
        v ? (
          <Tag color="blue" className="font-mono">
            已索引
          </Tag>
        ) : (
          <span className="text-tertiary-fixed">—</span>
        ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 140,
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
          {r.status === 'pending' && (
            <>
              <Tooltip title="通过">
                <Button
                  type="text"
                  size="small"
                  icon={<Check size={14} />}
                  onClick={() => handleApprove(r)}
                />
              </Tooltip>
              <Tooltip title="拒绝">
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<XIcon size={14} />}
                  onClick={() => handleReject(r)}
                />
              </Tooltip>
            </>
          )}
          {r.status === 'approved' && !r.milvus_chunk_id && (
            <Tooltip title="写入向量库">
              <Button
                type="text"
                size="small"
                icon={<RefreshCw size={14} />}
                loading={reindexQa.isPending}
                onClick={() => reindexQa.mutate(r.id)}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
            问题审核
          </h1>
          <p className="font-mono text-label-mono text-on-surface-variant mt-2 uppercase tracking-widest">
            QA REVIEW · 文章入库自动生成的问题与答案
          </p>
        </div>
        <Select
          value={statusFilter}
          onChange={setStatusFilter}
          options={STATUS_OPTIONS}
          style={{ width: 140 }}
        />
      </div>

      <Table<AdminQaPair>
        rowKey="id"
        columns={columns}
        dataSource={data?.items}
        loading={isLoading || isFetching}
        pagination={false}
        size="middle"
      />

      <Modal
        open={editing.open}
        title="编辑 Q&A"
        onCancel={() => {
          setEditing({ open: false });
          form.resetFields();
        }}
        okText="保存并通过"
        cancelText="取消"
        confirmLoading={reviewQa.isPending}
        onOk={() => form.submit()}
        width={720}
        destroyOnHidden
      >
        <Form<EditFormValues>
          form={form}
          layout="vertical"
          onFinish={onSubmit}
          requiredMark={false}
        >
          <Form.Item
            name="question"
            label={fieldLabel('问题')}
            rules={[{ required: true, message: '请输入问题' }]}
          >
            <Input.TextArea
              autoSize={{ minRows: 2, maxRows: 4 }}
              placeholder="用户可能提出的问题"
            />
          </Form.Item>
          <Form.Item
            name="answer"
            label={fieldLabel('答案')}
            rules={[{ required: true, message: '请输入答案' }]}
          >
            <Input.TextArea
              autoSize={{ minRows: 4, maxRows: 10 }}
              placeholder="基于文章内容的答案"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
