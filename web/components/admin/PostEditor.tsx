'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { App, Button, Form, Input, InputNumber, Select, Space } from 'antd';
import { ArrowLeft, Check } from 'lucide-react';
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
import MarkdownEditor from '@/components/editor/MarkdownEditor';
import { slugify } from '@/lib/utils';

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

/** 草稿自动保存间隔(毫秒) */
const AUTOSAVE_DELAY = 5000;

/**
 * 后台文章编辑器(共用新建/编辑)。
 *
 * 功能:
 * - slug 自动生成:title 变化时,若 slug 未被手动编辑过,自动从 title 生成
 * - 草稿自动保存:编辑模式下,内容变更后防抖 5s 自动保存(仅 draft 状态)
 * - Bytemd 源码 + 预览分屏,插件链与博客展示端一致
 *
 * 编辑模式传入 post 时,会预填表单。
 */
export default function PostEditor({ post }: { post?: AdminPost }) {
  const router = useRouter();
  const { message } = App.useApp();
  const [form] = Form.useForm<FormValues>();
  const isEdit = !!post;

  // slug 是否被用户手动编辑过(若否,则跟随 title 自动生成)
  const slugTouchedRef = useRef(false);

  // 自动保存状态
  const [autoSaveStatus, setAutoSaveStatus] = useState<
    'idle' | 'pending' | 'saving' | 'saved'
  >('idle');
  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latestValuesRef = useRef<FormValues | null>(null);

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
    onSuccess: () => {
      // 手动保存时不弹 message,由 autoSaveStatus 提示
    },
    onError: (e) => {
      message.error(e.message);
      setAutoSaveStatus('idle');
    },
  });

  // 预填表单
  useEffect(() => {
    if (!post) return;
    slugTouchedRef.current = true; // 编辑模式不自动覆盖已有 slug
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

  // title 变化时自动生成 slug(仅新建模式 或 slug 未被手动编辑时)
  const handleTitleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const title = e.target.value;
      form.setFieldValue('title', title);
      if (!slugTouchedRef.current) {
        form.setFieldValue('slug', slugify(title));
      }
    },
    [form],
  );

  // slug 字段被手动编辑时,标记 touched
  const handleSlugChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      slugTouchedRef.current = true;
      form.setFieldValue('slug', e.target.value);
    },
    [form],
  );

  // 草稿自动保存:监听表单变化,防抖 5s 后保存
  const triggerAutoSave = useCallback(
    (values: FormValues) => {
      if (!isEdit || !post) return;
      if (values.status !== 'draft') return; // 仅草稿自动保存
      if (autoSaveStatus === 'saving') return;

      latestValuesRef.current = values;
      setAutoSaveStatus('pending');

      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
      autoSaveTimerRef.current = setTimeout(async () => {
        const v = latestValuesRef.current;
        if (!v || !post) return;
        setAutoSaveStatus('saving');
        const payload: PostUpdatePayload = {
          slug: v.slug,
          title: v.title,
          excerpt: v.excerpt || null,
          channel_id: v.channel_id,
          tags: v.tags?.length ? v.tags : null,
          content_md: v.content_md,
          status: v.status,
          reading_time: v.reading_time || null,
        };
        try {
          await updatePost.mutateAsync({ id: post.id, payload });
          setAutoSaveStatus('saved');
        } catch {
          setAutoSaveStatus('idle');
        }
      }, AUTOSAVE_DELAY);
    },
    [isEdit, post, autoSaveStatus, updatePost],
  );

  // 清理定时器
  useEffect(() => {
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, []);

  const onFinish = (values: FormValues) => {
    // 提交前取消未执行的自动保存
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
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
      updatePost.mutate(
        { id: post.id, payload },
        {
          onSuccess: () => {
            message.success('已保存');
            setAutoSaveStatus('idle');
          },
        },
      );
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
          {/* 草稿自动保存状态指示 */}
          {isEdit && autoSaveStatus !== 'idle' && (
            <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest flex items-center gap-1">
              {autoSaveStatus === 'pending' && <span className="text-tertiary-fixed">编辑中…</span>}
              {autoSaveStatus === 'saving' && <span className="text-tertiary-fixed">保存中…</span>}
              {autoSaveStatus === 'saved' && (
                <>
                  <Check size={12} className="text-primary" />
                  <span className="text-primary">已自动保存</span>
                </>
              )}
            </span>
          )}
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
        onValuesChange={(_, allValues) => triggerAutoSave(allValues)}
        initialValues={{
          status: 'draft',
        }}
        requiredMark={false}
      >
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-6">
          {/* 主区:标题 + 正文 */}
          <div className="space-y-4">
            <Form.Item
              name="title"
              label={fieldLabel('标题')}
              rules={[{ required: true, message: '请输入标题' }]}
            >
              <Input
                size="large"
                placeholder="文章标题"
                onChange={handleTitleChange}
              />
            </Form.Item>

            <Form.Item
              name="content_md"
              label={fieldLabel('正文(Markdown · 源码/预览分屏)')}
              rules={[{ required: true, message: '请输入正文' }]}
              extra={
                <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
                  BYTEMD · GFM / HIGHLIGHT / MATH / MERMAID · 粘贴或拖拽图片自动上传
                </span>
              }
            >
              <MarkdownEditor placeholder="## 标题&#10;&#10;支持 GFM、代码高亮、数学公式、Mermaid 图表" />
            </Form.Item>

            <Form.Item
              name="excerpt"
              label={fieldLabel('摘要')}
              extra={
                <span className="font-mono text-label-mono text-tertiary-fixed">
                  留空则从正文首段自动生成
                </span>
              }
            >
              <Input.TextArea
                autoSize={{ minRows: 2, maxRows: 4 }}
                placeholder="一行简介(留空自动生成)"
              />
            </Form.Item>
          </div>

          {/* 侧栏:元信息 */}
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
                extra={
                  <span className="font-mono text-label-mono text-tertiary-fixed">
                    留空则从标题自动生成
                  </span>
                }
                rules={[
                  { required: true, message: '请输入 slug' },
                  {
                    pattern: /^[a-z0-9\u4e00-\u9fff-]+$/,
                    message: '只能小写字母/数字/中文/连字符',
                  },
                ]}
              >
                <Input
                  placeholder="url-friendly-slug"
                  onChange={handleSlugChange}
                />
              </Form.Item>

              <Form.Item name="tags" label={fieldLabel('标签')}>
                <Select
                  mode="tags"
                  placeholder="按回车添加"
                  tokenSeparators={[',', ' ']}
                />
              </Form.Item>

              <Form.Item
                name="reading_time"
                label={fieldLabel('阅读时长(分)')}
                extra={
                  <span className="font-mono text-label-mono text-tertiary-fixed">
                    留空则按字数自动计算
                  </span>
                }
              >
                <InputNumber
                  min={0}
                  max={300}
                  className="w-full"
                  placeholder="自动计算"
                />
              </Form.Item>
            </div>

            {/* 派生字段提示 */}
            <div className="border border-outline-variant bg-surface-container-lowest/60 p-4 space-y-2">
              <h4 className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest mb-2">
                自动派生
              </h4>
              <div className="space-y-1.5">
                <DeriveRow label="Slug" hint="从标题生成" />
                <DeriveRow label="摘要" hint="从正文首段提取" />
                <DeriveRow label="阅读时长" hint="按中英文字数估算" />
                <DeriveRow label="目录" hint="从标题层级生成" />
              </div>
              <p className="font-mono text-label-mono text-tertiary-fixed mt-2">
                未显式提供的字段将在保存时自动生成
              </p>
            </div>

            {isEdit && post?.updated_at && (
              <div className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest px-1">
                UPDATED · {new Date(post.updated_at).toLocaleString('zh-CN')}
              </div>
            )}
          </div>
        </div>

        {/* 提交触发:通过 form.submit() 触发,这里不需要按钮 */}
        <button type="submit" className="hidden" aria-hidden />
      </Form>
    </div>
  );
}

function DeriveRow({ label, hint }: { label: string; hint: string }) {
  return (
    <div className="flex items-center justify-between font-mono text-label-mono">
      <span className="text-on-surface-variant">{label}</span>
      <span className="text-tertiary-fixed">{hint}</span>
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
