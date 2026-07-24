'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { App, Button, Form, Input, Select, Space, Tag, Tooltip } from 'antd';
import {
  ArrowLeft,
  Check,
  Link2,
  Plus,
  FileText,
} from 'lucide-react';
import {
  useAdminChannels,
  useCreateKbNote,
  useKbBacklinks,
  useKbTemplates,
  useUpdateKbNote,
} from '@/hooks/useAdmin';
import {
  kbApi,
  type KbNote,
  type KbNoteCreatePayload,
  type KbNoteUpdatePayload,
} from '@/lib/api/admin';
import MarkdownEditor from '@/components/editor/MarkdownEditor';
import type { WikilinkItem } from '@/components/editor/WikilinkSuggest';
import { slugify } from '@/lib/utils';

type FormValues = {
  slug: string;
  title: string;
  excerpt?: string;
  category: string;
  folder_path?: string;
  content_md: string;
  channel_id?: string; // published 必填，draft/private 可空
  tags?: string[];
  status: string;
  is_moc?: boolean;
  source_url?: string;
};

const STATUS_OPTIONS = [
  { label: '草稿', value: 'draft' },
  { label: '私有', value: 'private' },
  { label: '已发布', value: 'published' },
];

const CATEGORY_OPTIONS = [
  { label: '00 收集箱', value: 'inbox' },
  { label: '01 每日笔记', value: 'daily' },
  { label: '02 阅读笔记', value: 'reading' },
  { label: '03 主题知识', value: 'knowledge' },
  { label: '04 项目资料', value: 'projects' },
  { label: '05 模板库', value: 'templates' },
];

/** 草稿自动保存间隔(毫秒) */
const AUTOSAVE_DELAY = 5000;

/**
 * 知识库笔记编辑器（共用新建/编辑）。
 *
 * 功能：
 * - 复用 Bytemd Markdown 编辑器（与文章编辑器一致，支持图片粘贴/拖拽上传）
 * - 侧栏：category/folder_path/status/tags/is_moc/source_url 元信息
 * - 反链面板：显示哪些笔记引用了当前笔记（编辑模式）
 * - 出链列表：显示当前笔记引用了哪些笔记（含悬空链接）
 * - 草稿自动保存：5s 防抖，仅 draft 状态
 * - 模板注入：新建时可选择模板，自动填充 content_md
 */
export default function NoteEditor({ note }: { note?: KbNote }) {
  const router = useRouter();
  const { message } = App.useApp();
  const [form] = Form.useForm<FormValues>();
  const isEdit = !!note;

  const slugTouchedRef = useRef(false);

  const [autoSaveStatus, setAutoSaveStatus] = useState<
    'idle' | 'pending' | 'saving' | 'saved'
  >('idle');
  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latestValuesRef = useRef<FormValues | null>(null);

  // 模板列表（新建模式才需要）
  const { data: templates } = useKbTemplates(undefined, { enabled: !isEdit });

  // 频道列表（发布时必选）
  const { data: channelsData, isLoading: channelsLoading } = useAdminChannels({
    size: 200,
  });

  const createNote = useCreateKbNote({
    onSuccess: (data) => {
      message.success('已创建');
      router.push(`/admin/knowledge/${data.id}/edit`);
    },
    onError: (e) => message.error(e.message),
  });

  const updateNote = useUpdateKbNote({
    onSuccess: () => {
      // 自动保存不弹 message，由 autoSaveStatus 提示
    },
    onError: (e) => {
      message.error(e.message);
      setAutoSaveStatus('idle');
    },
  });

  // 反链面板（编辑模式）
  const { data: backlinks } = useKbBacklinks(note?.id || '', {
    enabled: !!note,
  });

  // 预填表单
  useEffect(() => {
    if (!note) return;
    slugTouchedRef.current = true;
    form.setFieldsValue({
      slug: note.slug,
      title: note.title,
      excerpt: note.excerpt || undefined,
      category: note.category,
      folder_path: note.folder_path || undefined,
      content_md: note.content_md,
      channel_id: note.channel_id || undefined,
      tags: note.tags || [],
      status: note.status,
      is_moc: note.is_moc,
      source_url: note.source_url || undefined,
    });
  }, [note, form]);

  // title 变化时自动生成 slug
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

  const handleSlugChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      slugTouchedRef.current = true;
      form.setFieldValue('slug', e.target.value);
    },
    [form],
  );

  // 模板选择：填充 content_md
  const handleTemplate = useCallback(
    (templateId: string) => {
      const tpl = templates?.find((t) => t.id === templateId);
      if (!tpl) return;
      const current = form.getFieldValue('content_md') || '';
      // 简单替换占位符 {{date}}
      const today = new Date().toISOString().slice(0, 10);
      const filled = tpl.content_md
        .replace(/\{\{date\}\}/g, today)
        .replace(/\{\{title\}\}/g, form.getFieldValue('title') || '')
        .replace(/\{\{topic\}\}/g, form.getFieldValue('title') || '')
        .replace(/\{\{book_title\}\}/g, form.getFieldValue('title') || '');
      form.setFieldValue('content_md', current + (current ? '\n\n' : '') + filled);
      if (!form.getFieldValue('category')) {
        form.setFieldValue('category', tpl.category);
      }
      message.success(`已套用模板：${tpl.name}`);
    },
    [templates, form, message],
  );

  // 双链笔记搜索（供 MarkdownEditor 调用）
  const searchNotes = useCallback(async (q: string): Promise<WikilinkItem[]> => {
    const res = await kbApi.listNotes({ q: q || undefined, size: 10 });
    return res.items.map((i) => ({ id: i.id, title: i.title }));
  }, []);

  // 草稿自动保存
  const triggerAutoSave = useCallback(
    (values: FormValues) => {
      if (!isEdit || !note) return;
      if (values.status !== 'draft') return;
      if (autoSaveStatus === 'saving') return;

      latestValuesRef.current = values;
      setAutoSaveStatus('pending');

      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
      autoSaveTimerRef.current = setTimeout(async () => {
        const v = latestValuesRef.current;
        if (!v || !note) return;
        setAutoSaveStatus('saving');
        const payload: KbNoteUpdatePayload = {
          slug: v.slug,
          title: v.title,
          excerpt: v.excerpt || null,
          category: v.category,
          folder_path: v.folder_path || null,
          content_md: v.content_md,
          tags: v.tags?.length ? v.tags : null,
          status: v.status,
          is_moc: v.is_moc || false,
          source_url: v.source_url || null,
        };
        try {
          await updateNote.mutateAsync({ id: note.id, payload });
          setAutoSaveStatus('saved');
        } catch {
          setAutoSaveStatus('idle');
        }
      }, AUTOSAVE_DELAY);
    },
    [isEdit, note, autoSaveStatus, updateNote],
  );

  useEffect(() => {
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, []);

  const onFinish = (values: FormValues) => {
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
    const tags = values.tags?.length ? values.tags : null;
    // published 必须有 channel；draft/private 可无
    const channelId =
      values.status === 'published' ? values.channel_id : values.channel_id || null;
    if (isEdit && note) {
      const payload: KbNoteUpdatePayload = {
        slug: values.slug,
        title: values.title,
        excerpt: values.excerpt || null,
        category: values.category,
        folder_path: values.folder_path || null,
        content_md: values.content_md,
        channel_id: channelId,
        tags,
        status: values.status,
        is_moc: values.is_moc || false,
        source_url: values.source_url || null,
      };
      updateNote.mutate(
        { id: note.id, payload },
        {
          onSuccess: () => {
            message.success('已保存');
            setAutoSaveStatus('idle');
          },
        },
      );
    } else {
      const payload: KbNoteCreatePayload = {
        slug: values.slug,
        title: values.title,
        excerpt: values.excerpt || null,
        category: values.category || 'inbox',
        folder_path: values.folder_path || null,
        content_md: values.content_md,
        channel_id: channelId,
        tags,
        status: values.status || 'draft',
        is_moc: values.is_moc || false,
        source_url: values.source_url || null,
      };
      createNote.mutate(payload);
    }
  };

  const submitting = createNote.isPending || updateNote.isPending;

  return (
    <div>
      <div className="flex items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <Link href="/admin/knowledge">
            <Button type="text" icon={<ArrowLeft size={16} />} />
          </Link>
          <div>
            <h1 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
              {isEdit ? '编辑笔记' : '新建笔记'}
            </h1>
            <p className="font-mono text-label-mono text-on-surface-variant mt-1 uppercase tracking-widest">
              {isEdit ? `NOTE · ${note?.slug}` : 'NEW NOTE'}
            </p>
          </div>
        </div>
        <Space>
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
          <Link href="/admin/knowledge">
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
          category: 'inbox',
        }}
        requiredMark={false}
      >
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
          {/* 主区：标题 + 正文 */}
          <div className="space-y-4 min-w-0">
            <Form.Item
              name="title"
              label={fieldLabel('标题')}
              rules={[{ required: true, message: '请输入标题' }]}
            >
              <Input
                size="large"
                placeholder="笔记标题（双链 [[标题]] 会按此匹配）"
                onChange={handleTitleChange}
              />
            </Form.Item>

            {!isEdit && templates && templates.length > 0 && (
              <Form.Item label={fieldLabel('套用模板（可选）')}>
                <Select
                  placeholder="选择模板自动填充正文"
                  allowClear
                  onChange={handleTemplate}
                  options={templates.map((t) => ({
                    label: `${t.name}（${t.category}）`,
                    value: t.id,
                  }))}
                />
              </Form.Item>
            )}

            <Form.Item
              name="content_md"
              label={fieldLabel('正文（Markdown · 源码/预览分屏）')}
              rules={[{ required: true, message: '请输入正文' }]}
              extra={
                <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
                  BYTEMD · GFM / HIGHLIGHT / MATH / MERMAID · [[双链]] · #标签 · 粘贴/拖拽图片自动上传
                </span>
              }
            >
              <MarkdownEditor
                placeholder="## 标题&#10;&#10;支持 [[双链]]、#标签、GFM、代码高亮、数学公式、Mermaid"
                enableWikilink
                searchNotes={searchNotes}
                excludeNoteId={note?.id}
              />
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
                placeholder="一行简介（留空自动生成）"
              />
            </Form.Item>
          </div>

          {/* 侧栏：元信息 + 反链/出链 */}
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
                noStyle
                shouldUpdate={(prev, cur) => prev.status !== cur.status}
              >
                {({ getFieldValue }) => {
                  const isPublished = getFieldValue('status') === 'published';
                  return (
                    <Form.Item
                      name="channel_id"
                      label={fieldLabel('频道')}
                      rules={[
                        {
                          required: isPublished,
                          message: '发布到博客必须选择频道',
                        },
                      ]}
                      extra={
                        <span className="font-mono text-label-mono text-tertiary-fixed">
                          {isPublished
                            ? '发布到博客必填'
                            : '私有/草稿可不选'}
                        </span>
                      }
                    >
                      <Select
                        loading={channelsLoading}
                        placeholder="选择频道"
                        allowClear={!isPublished}
                        options={(channelsData?.items || []).map((c) => ({
                          label: c.name,
                          value: c.id,
                        }))}
                      />
                    </Form.Item>
                  );
                }}
              </Form.Item>

              <Form.Item
                name="category"
                label={fieldLabel('分类目录')}
                rules={[{ required: true }]}
              >
                <Select options={CATEGORY_OPTIONS} />
              </Form.Item>

              <Form.Item
                name="folder_path"
                label={fieldLabel('子目录')}
                extra={
                  <span className="font-mono text-label-mono text-tertiary-fixed">
                    仅 knowledge/projects 用，如 knowledge/大模型
                  </span>
                }
              >
                <Input placeholder="knowledge/大模型" />
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
                <Input placeholder="url-friendly-slug" onChange={handleSlugChange} />
              </Form.Item>

              <Form.Item name="tags" label={fieldLabel('标签')}>
                <Select
                  mode="tags"
                  placeholder="按回车添加"
                  tokenSeparators={[',', ' ']}
                />
              </Form.Item>

              <Form.Item name="is_moc" label={fieldLabel('MOC 主题地图')}>
                <Select
                  options={[
                    { label: '否', value: false },
                    { label: '是（主题地图节点）', value: true },
                  ]}
                />
              </Form.Item>

              <Form.Item
                name="source_url"
                label={fieldLabel('来源 URL')}
                extra={
                  <span className="font-mono text-label-mono text-tertiary-fixed">
                    阅读笔记的原文链接
                  </span>
                }
              >
                <Input placeholder="https://..." />
              </Form.Item>
            </div>

            {/* 出链列表（编辑模式） */}
            {isEdit && note?.outlinks && note.outlinks.length > 0 && (
              <div className="border border-outline-variant bg-surface-container-lowest p-4">
                <div className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest mb-3 flex items-center gap-2">
                  <Link2 size={12} />
                  出链 · {note.outlinks.length}
                </div>
                <div className="space-y-1.5">
                  {note.outlinks.map((link) => (
                    <div key={link.id} className="flex items-center gap-2 text-sm">
                      <span className="text-tertiary-fixed font-mono">[[</span>
                      {link.target_note_id ? (
                        <Link
                          href={`/admin/knowledge/${link.target_note_id}/edit`}
                          className="text-primary hover:underline truncate"
                        >
                          {link.target_title_raw}
                        </Link>
                      ) : (
                        <span className="text-tertiary-fixed italic truncate">
                          {link.target_title_raw}（悬空）
                        </span>
                      )}
                      <span className="text-tertiary-fixed font-mono">]]</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 反链面板（编辑模式） */}
            {isEdit && (
              <div className="border border-outline-variant bg-surface-container-lowest p-4">
                <div className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest mb-3 flex items-center gap-2">
                  <Link2 size={12} />
                  反链 · {backlinks?.length || 0}
                </div>
                {backlinks && backlinks.length > 0 ? (
                  <div className="space-y-1.5">
                    {backlinks.map((link) => (
                      <Link
                        key={link.id}
                        href={
                          link.source_note_id
                            ? `/admin/knowledge/${link.source_note_id}/edit`
                            : '#'
                        }
                        className="flex items-center gap-2 text-sm hover:text-primary transition-colors"
                      >
                        <FileText size={12} className="text-tertiary-fixed shrink-0" />
                        <span className="truncate">{link.source_title}</span>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <p className="font-mono text-label-mono text-tertiary-fixed">
                    暂无反链
                  </p>
                )}
              </div>
            )}

            {isEdit && note?.updated_at && (
              <div className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest px-1">
                UPDATED · {new Date(note.updated_at).toLocaleString('zh-CN')}
              </div>
            )}
          </div>
        </div>

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
