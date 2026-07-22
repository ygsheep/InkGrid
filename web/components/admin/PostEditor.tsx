'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { App, Button, Form, Input, InputNumber, Select, Space } from 'antd';
import { ArrowLeft } from 'lucide-react';
import {
  useAdminChannels,
  useCreatePost,
  useUpdatePost,
} from '@/hooks/useAdmin';
import type {
  AdminPost,
  PostCreatePayload,
  PostUpdatePayload,
} from '@/lib/api/admin';

type FormValues = {
  slug: string;
  title: string;
  excerpt?: string;
  channel_id: string;
  tags?: string[];
  content_md: string;
  status: string;
  reading_time?: number;
};

const STATUS_OPTIONS = [
  { label: '草稿', value: 'draft' },
  { label: '已发布', value: 'published' },
  { label: '已归档', value: 'archived' },
];

/**
 * 后台文章编辑器（共用新建/编辑）。
 * P0 阶段先用 textarea；后续接入 Bytemd 源码+预览编辑器。
 *
 * 编辑模式传入 post 时，会预填表单。
 */
export default function PostEditor({ post }: { post?: AdminPost }) {
  const router = useRouter();
  const { message } = App.useApp();
  const [form] = Form.useForm<FormValues>();
  const isEdit = !!post;

  // 频道列表
  const { data: channelsData, isLoading: channelsLoading } = useAdminChannels({
    size: 200,
  });

  const createPost = useCreatePost({
    onSuccess: (data) => {
      message.success('已创建');
      router.push(`/admin/posts/${data.id}/edit`);
    },
    onError: (e) => message.error(e.message),
  });

  const updatePost = useUpdatePost({
    onSuccess: () => message.success('已保存'),
    onError: (e) => message.error(e.message),
  });

  // 预填表单
  useEffect(() => {
    if (!post) return;
    form.setFieldsValue({
      slug: post.slug,
      title: post.title,
      excerpt: post.excerpt || undefined,
      channel_id: post.channel_id,
      tags: post.tags || [],
      content_md: post.content,
      status: post.status,
      reading_time: post.reading_time || undefined,
    });
  }, [post, form]);

  const onFinish = (values: FormValues) => {
    const tags = values.tags?.length ? values.tags : null;
    if (isEdit && post) {
      const payload: PostUpdatePayload = {
        slug: values.slug,
        title: values.title,
        excerpt: values.excerpt || null,
        channel_id: values.channel_id,
        tags,
        content_md: values.content_md,
        status: values.status,
        reading_time: values.reading_time || null,
      };
      updatePost.mutate({ id: post.id, payload });
    } else {
      const payload: PostCreatePayload = {
        slug: values.slug,
        title: values.title,
        excerpt: values.excerpt || null,
        channel_id: values.channel_id,
        tags,
        content_md: values.content_md,
        status: values.status,
        reading_time: values.reading_time || null,
      };
      createPost.mutate(payload);
    }
  };

  const submitting = createPost.isPending || updatePost.isPending;

  return (
    <div>
      <div className="flex items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <Link href="/admin/posts">
            <Button type="text" icon={<ArrowLeft size={16} />} />
          </Link>
          <div>
            <h1 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
              {isEdit ? '编辑文章' : '写文章'}
            </h1>
            <p className="font-mono text-label-mono text-on-surface-variant mt-1 uppercase tracking-widest">
              {isEdit ? `EDIT · ${post?.slug}` : 'NEW'}
            </p>
          </div>
        </div>
        <Space>
          <Link href="/admin/posts">
            <Button>取消</Button>
          </Link>
          <Button
            type="primary"
            onClick={() => form.submit()}
            loading={submitting}
          >
            {isEdit ? '保存' : '创建'}
          </Button>
        </Space>
      </div>

      <Form<FormValues>
        form={form}
        layout="vertical"
        onFinish={onFinish}
        initialValues={{
          status: 'draft',
        }}
        requiredMark={false}
      >
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-6">
          {/* 主区：标题 + 正文 */}
          <div className="space-y-4">
            <Form.Item
              name="title"
              label={fieldLabel('标题')}
              rules={[{ required: true, message: '请输入标题' }]}
            >
              <Input size="large" placeholder="文章标题" />
            </Form.Item>

            <Form.Item
              name="content_md"
              label={fieldLabel('正文（Markdown）')}
              rules={[{ required: true, message: '请输入正文' }]}
              extra={
                <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
                  TEXTAREA · 后续接入 BYTEMD 编辑器
                </span>
              }
            >
              <Input.TextArea
                autoSize={{ minRows: 20, maxRows: 40 }}
                placeholder="## 标题&#10;&#10;支持 Markdown 语法"
                className="font-mono text-body-md"
                style={{ fontFamily: 'var(--font-jetbrains), monospace' }}
              />
            </Form.Item>

            <Form.Item name="excerpt" label={fieldLabel('摘要')}>
              <Input.TextArea
                autoSize={{ minRows: 2, maxRows: 4 }}
                placeholder="一行简介（可空）"
              />
            </Form.Item>
          </div>

          {/* 侧栏：元信息 */}
          <div className="space-y-4">
            <div className="border border-outline-variant bg-surface-container-lowest p-4 space-y-4">
              <Form.Item
                name="status"
                label={fieldLabel('状态')}
                rules={[{ required: true }]}
              >
                <Select options={STATUS_OPTIONS} />
              </Form.Item>

              <Form.Item
                name="channel_id"
                label={fieldLabel('频道')}
                rules={[{ required: true, message: '请选择频道' }]}
              >
                <Select
                  loading={channelsLoading}
                  placeholder="选择频道"
                  options={(channelsData?.items || []).map((c) => ({
                    label: c.name,
                    value: c.id,
                  }))}
                />
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

              <Form.Item name="tags" label={fieldLabel('标签')}>
                <Select
                  mode="tags"
                  placeholder="按回车添加"
                  tokenSeparators={[',', ' ']}
                />
              </Form.Item>

              <Form.Item name="reading_time" label={fieldLabel('阅读时长(分)')}>
                <InputNumber
                  min={0}
                  max={300}
                  className="w-full"
                  placeholder="自动计算可空"
                />
              </Form.Item>
            </div>

            {isEdit && post?.updated_at && (
              <div className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest px-1">
                UPDATED · {new Date(post.updated_at).toLocaleString('zh-CN')}
              </div>
            )}
          </div>
        </div>

        {/* 提交触发：通过 form.submit() 触发，这里不需要按钮 */}
        <button type="submit" className="hidden" aria-hidden />
      </Form>
    </div>
  );
}

function fieldLabel(text: string) {
  return (
    <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
      {text}
    </span>
  );
}
