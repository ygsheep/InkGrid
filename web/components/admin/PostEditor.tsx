'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { App, Form } from 'antd';
import { ArrowLeft, Settings2, Save, Plus } from 'lucide-react';
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
import PostMetaDrawer, {
  type PostMetaValues,
} from '@/components/editor/PostMetaDrawer';
import EditorStatusBar from '@/components/editor/EditorStatusBar';
import EditorShell from '@/components/editor/EditorShell';
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

/** 草稿自动保存间隔(毫秒) */
const AUTOSAVE_DELAY = 5000;

/** PostMetaValues 初始值 */
const META_VALUES_INIT: PostMetaValues = {
  status: 'draft',
  channel_id: undefined,
  slug: '',
  tags: [],
  excerpt: '',
  reading_time: null,
};

/**
 * 后台文章编辑器（共用新建/编辑）。
 *
 * 三段式布局（与 NoteEditor 一致，通过 EditorShell 共用）：
 * - 顶部条：返回 / 面包屑 / 保存状态 / META 按钮 / 状态徽章 / 保存按钮
 * - 写作区：占满宽度，hero 标题 + 全宽编辑器
 * - 底部条：字数 / 阅读 / 出链
 *
 * 功能：
 * - slug 自动生成：title 变化时，若 slug 未被手动编辑过，自动从 title 生成
 * - 草稿自动保存：编辑模式下，内容变更后防抖 5s 自动保存（仅 draft 状态）
 * - META 抽屉：状态/频道/Slug/标签/阅读时长/摘要 收进浮层
 */
export default function PostEditor({ post }: { post?: AdminPost }) {
  const router = useRouter();
  const { message } = App.useApp();
  const [form] = Form.useForm<FormValues>();
  const isEdit = !!post;

  const slugTouchedRef = useRef(false);
  const metaTriggerRef = useRef<HTMLButtonElement>(null);

  // Refs 用于在异步回调中获取最新 state
  const contentMdRef = useRef('');
  const titleValueRef = useRef('');
  const statusValueRef = useRef('draft');
  const metaValuesRef = useRef(META_VALUES_INIT);

  const [autoSaveStatus, setAutoSaveStatus] = useState<
    'idle' | 'pending' | 'saving' | 'saved'
  >('idle');
  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [metaDrawerVisible, setMetaDrawerVisible] = useState(false);
  const [editorMode, setEditorMode] = useState<'split' | 'tab' | 'preview'>('split');

  // 实时内容（用于字数/出链统计）
  const [contentMd, setContentMd] = useState('');
  const [titleValue, setTitleValue] = useState('');

  // MetaDrawer 需要的完整表单值（避免 render 阶段调 form.getFieldValue）
  const [statusValue, setStatusValue] = useState('draft');
  const [metaValues, setMetaValues] = useState(META_VALUES_INIT);

  // 同步 refs（在 render 阶段同步，确保异步回调能读到最新值）
  contentMdRef.current = contentMd;
  titleValueRef.current = titleValue;
  statusValueRef.current = statusValue;
  metaValuesRef.current = metaValues;

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
      // 自动保存不弹 message，由 autoSaveStatus 提示
    },
    onError: (e) => {
      message.error(e.message);
      setAutoSaveStatus('idle');
    },
  });

  // 预填表单
  useEffect(() => {
    if (!post) return;
    slugTouchedRef.current = true;
    form.setFieldsValue({
      slug: post.slug,
      title: post.title,
      excerpt: post.excerpt || undefined,
      channel_id: post.channel_id || undefined,
      tags: post.tags || [],
      content_md: post.content,
      status: post.status,
      reading_time: post.reading_time || undefined,
    });
    setTitleValue(post.title);
    setContentMd(post.content);
    setStatusValue(post.status);
    setMetaValues({
      status: post.status,
      channel_id: post.channel_id || undefined,
      slug: post.slug,
      tags: post.tags || [],
      excerpt: post.excerpt || '',
      reading_time: post.reading_time ?? null,
    });
  }, [post, form]);

  // title 变化时自动生成 slug
  const handleTitleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const title = e.target.value;
      titleValueRef.current = title;
      setTitleValue(title);
      form.setFieldValue('title', title);
      if (!slugTouchedRef.current) {
        const slug = slugify(title);
        form.setFieldValue('slug', slug);
        setMetaValues((m) => ({ ...m, slug }));
      }
    },
    [form],
  );

  /** 统一字段变化处理：Form.onValuesChange 和 PostMetaDrawer.onFieldChange 共用 */
  const handleFieldChange = useCallback((field: string, value: unknown) => {
    switch (field) {
      case 'status':
        setStatusValue((value as string) || 'draft');
        setMetaValues((m) => ({ ...m, status: (value as string) || 'draft' }));
        break;
      case 'channel_id':
        setMetaValues((m) => ({ ...m, channel_id: value as string | undefined }));
        break;
      case 'slug':
        setMetaValues((m) => ({ ...m, slug: (value as string) || '' }));
        break;
      case 'tags':
        setMetaValues((m) => ({ ...m, tags: (value as string[]) || [] }));
        break;
      case 'excerpt':
        setMetaValues((m) => ({ ...m, excerpt: (value as string) || '' }));
        break;
      case 'reading_time':
        setMetaValues((m) => ({ ...m, reading_time: (value as number | null) ?? null }));
        break;
      case 'content_md':
        setContentMd((value as string) || '');
        break;
      case 'title':
        setTitleValue((value as string) || '');
        break;
    }
  }, []);

  const onValuesChangeHandler = useCallback(
    (changed: Partial<FormValues>, _allValues: FormValues) => {
      for (const field of Object.keys(changed) as (keyof FormValues)[]) {
        handleFieldChange(field, changed[field]);
      }
    },
    [handleFieldChange],
  );

  // 草稿自动保存（从 ref 读取最新 state，避免闭包陷阱）
  const triggerAutoSave = useCallback(() => {
    if (autoSaveStatus === 'saving') return;
    if (!isEdit || !post) return;
    if (statusValueRef.current !== 'draft') return; // 仅草稿自动保存

    setAutoSaveStatus('pending');

    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
    autoSaveTimerRef.current = setTimeout(async () => {
      if (!post) return;
      setAutoSaveStatus('saving');
      const mv = metaValuesRef.current;
      // channel_id 仅在有效 UUID 时传入，避免发送 "None" / 空字符串等非法值
      const channelId = mv.channel_id || post.channel_id || undefined;
      const payload: PostUpdatePayload = {
        slug: mv.slug || slugify(titleValueRef.current) || post.slug,
        title: titleValueRef.current || post.title,
        excerpt: mv.excerpt || null,
        ...(channelId ? { channel_id: channelId } : {}),
        tags: mv.tags?.length ? mv.tags : null,
        content_md: contentMdRef.current,
        status: mv.status,
        reading_time: mv.reading_time ?? null,
      };
      try {
        await updatePost.mutateAsync({ id: post.id, payload });
        setAutoSaveStatus('saved');
      } catch {
        setAutoSaveStatus('idle');
      }
    }, AUTOSAVE_DELAY);
  }, [isEdit, post, autoSaveStatus, updatePost]);

  // 清理定时器
  useEffect(() => {
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, []);

  const submitting = createPost.isPending || updatePost.isPending;

  // 提交：直接调用 mutation（用 state 构造 payload）
  const handleSubmit = useCallback(() => {
    if (statusValue === 'published' && !metaValues.channel_id) {
      message.error('发布文章必须选择频道（在 META 面板中设置）');
      setMetaDrawerVisible(true);
      return;
    }

    // 取消未执行的自动保存
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }

    const mv = metaValues;
    const title = titleValue || post?.title || '无标题文章';
    const slug = slugTouchedRef.current
      ? mv.slug || slugify(title)
      : slugify(title);
    const tags = mv.tags?.length ? mv.tags : null;
    // channel_id 仅在有效 UUID 时传入，避免发送 "None" / 空字符串等非法值
    const channelId = mv.channel_id || post?.channel_id || undefined;

    if (isEdit && post) {
      const payload: PostUpdatePayload = {
        slug,
        title,
        excerpt: mv.excerpt || null,
        ...(channelId ? { channel_id: channelId } : {}),
        tags,
        content_md: contentMd,
        status: mv.status,
        reading_time: mv.reading_time ?? null,
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
        slug,
        title,
        excerpt: mv.excerpt || null,
        channel_id: channelId || '',
        tags,
        content_md: contentMd,
        status: mv.status || 'draft',
        reading_time: mv.reading_time ?? null,
      };
      createPost.mutate(payload);
    }
  }, [statusValue, metaValues, message, isEdit, post, contentMd, titleValue,
      createPost, updatePost]);

  // ===== 实时统计 =====
  const stats = useMemo(() => {
    const text = contentMd || '';
    const cjk = (text.match(/[\u4e00-\u9fff]/g) || []).length;
    const en = (text.match(/[a-zA-Z]+/g) || []).length;
    const wordCount = cjk + en;
    const readingTime = Math.max(1, Math.ceil(cjk / 300 + en / 200));
    const outlinks = (text.match(/(?<!!)\[\[[^\]]+\]\]/g) || []).length;
    return { wordCount, readingTime, outlinks };
  }, [contentMd]);

  const onFinish = (_values: FormValues) => {
    // 保留 form.submit() 入口，但实际逻辑由 handleSubmit 直接处理
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
  };

  return (
    <Form<FormValues>
      form={form}
      layout="vertical"
      onFinish={onFinish}
      onValuesChange={onValuesChangeHandler}
      initialValues={{
        status: 'draft',
      }}
      requiredMark={false}
    >
      <EditorShell
        topBar={
          <>
            {/* ===== 左侧：返回 + 面包屑 ===== */}
            <div className="flex items-center gap-3">
              <Link
                href="/admin/posts"
                className="text-on-surface-variant hover:text-primary transition-colors"
              >
                <ArrowLeft size={16} />
              </Link>
              <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
                文章
                <span className="text-outline-variant mx-1">/</span>
                <span className="text-on-surface">
                  {isEdit ? post?.slug : '写文章'}
                </span>
              </span>
            </div>

            {/* ===== 右侧：保存状态 / META / 状态徽章 / 主操作 ===== */}
            <div className="relative flex items-center gap-3">
              {/* 保存状态 */}
              {isEdit && autoSaveStatus !== 'idle' && (
                <span className="font-mono text-label-mono uppercase tracking-widest flex items-center gap-1">
                  {autoSaveStatus === 'pending' && (
                    <span className="text-tertiary-fixed">编辑中…</span>
                  )}
                  {autoSaveStatus === 'saving' && (
                    <span className="text-tertiary-fixed">保存中…</span>
                  )}
                  {autoSaveStatus === 'saved' && (
                    <>
                      <span className="inline-block w-1.5 h-1.5 bg-tertiary-fixed" />
                      <span className="text-tertiary-fixed">已自动保存</span>
                    </>
                  )}
                </span>
              )}

              {/* META 按钮 */}
              <button
                ref={metaTriggerRef}
                type="button"
                onClick={() => setMetaDrawerVisible((v) => !v)}
                className={`flex items-center gap-1.5 font-mono text-label-mono uppercase tracking-widest px-2.5 py-1 border transition-colors ${
                  metaDrawerVisible
                    ? 'border-primary text-primary bg-surface-container-high'
                    : 'border-outline-variant text-on-surface-variant hover:text-primary hover:border-primary'
                }`}
              >
                <Settings2 size={12} />
                <span>META</span>
              </button>

              {/* 状态徽章 */}
              <span
                className={`font-mono text-label-mono uppercase tracking-widest px-2.5 py-1 border ${
                  statusValue === 'published'
                    ? 'border-tertiary-fixed text-tertiary-fixed'
                    : statusValue === 'archived'
                    ? 'border-outline text-on-surface-variant'
                    : 'border-outline-variant text-on-surface-variant'
                }`}
              >
                {statusValue === 'published'
                  ? 'PUBLISHED'
                  : statusValue === 'archived'
                  ? 'ARCHIVED'
                  : 'DRAFT'}
              </span>

              {/* 主操作按钮：创建/保存 */}
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitting}
                className="flex items-center gap-1.5 font-mono text-label-mono uppercase tracking-widest bg-primary text-on-primary px-3 py-1 hover:bg-primary-container transition-colors disabled:opacity-50"
              >
                {isEdit ? <Save size={12} /> : <Plus size={12} />}
                <span>{isEdit ? '保存' : '创建'}</span>
              </button>

              {/* 元信息抽屉 */}
              <PostMetaDrawer
                visible={metaDrawerVisible}
                onClose={() => setMetaDrawerVisible(false)}
                form={form}
                values={metaValues}
                onFieldChange={handleFieldChange}
                channels={channelsData?.items || []}
                channelsLoading={channelsLoading}
                isEdit={isEdit}
                slugTouchedRef={slugTouchedRef}
                triggerRef={metaTriggerRef}
              />
            </div>
          </>
        }
        bottomBar={
          <EditorStatusBar
            wordCount={stats.wordCount}
            readingTime={stats.readingTime}
            outlinksCount={stats.outlinks}
            backlinksCount={0}
            autoSaveStatus={autoSaveStatus}
            isEdit={isEdit}
          />
        }
      >
        {/* ===== 写作区（占满宽度）===== */}
        <div className="w-full px-6 lg:px-10 xl:px-14 py-6">
          {/* Hero 标题 */}
          <input
            type="text"
            placeholder="文章标题"
            value={titleValue}
            onChange={handleTitleChange}
            className="w-full bg-transparent border-none outline-none font-headline text-[28px] font-semibold text-primary leading-tight tracking-tighter placeholder:text-outline-variant focus:outline-none pb-1 border-b border-transparent focus:border-outline-variant transition-colors mb-3"
          />

          {/* 标题下方元信息（日期/频道/slug 预览） */}
          <div className="flex items-center gap-2 font-mono text-label-mono text-on-surface-variant uppercase tracking-widest mb-6">
            <span>
              {isEdit && post?.updated_at
                ? new Date(post.updated_at).toLocaleDateString('zh-CN')
                : new Date().toLocaleDateString('zh-CN')}
            </span>
            <span className="w-1 h-1 bg-outline-variant" />
            <span>
              {channelsData?.items?.find((c) => c.id === metaValues.channel_id)?.name ||
                '未选择频道'}
            </span>
            {titleValue && !slugTouchedRef.current && (
              <>
                <span className="w-1 h-1 bg-outline-variant" />
                <span className="text-tertiary-fixed/70">slug: {slugify(titleValue)}</span>
              </>
            )}
          </div>

          {/* 全宽编辑器 */}
          <MarkdownEditor
            value={contentMd}
            onChange={(val) => {
              contentMdRef.current = val;
              setContentMd(val);
              form.setFieldValue('content_md', val);
              triggerAutoSave();
            }}
            placeholder="## 标题&#10;&#10;支持 GFM、代码高亮、数学公式、Mermaid 图表&#10;&#10;粘贴或拖拽图片自动上传"
            mode={editorMode}
            onModeChange={setEditorMode}
          />
        </div>
      </EditorShell>

      <button type="submit" className="hidden" aria-hidden />
    </Form>
  );
}
