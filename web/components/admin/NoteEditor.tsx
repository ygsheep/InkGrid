'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { App, Form, Input } from 'antd';
import { ArrowLeft, Settings2, Plus, Save } from 'lucide-react';
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
import MetaDrawer from '@/components/editor/MetaDrawer';
import EditorStatusBar from '@/components/editor/EditorStatusBar';
import EditorShell from '@/components/editor/EditorShell';
import type { WikilinkItem } from '@/components/editor/WikilinkSuggest';
import { slugify } from '@/lib/utils';

type FormValues = {
  slug: string;
  title: string;
  excerpt?: string;
  category: string;
  folder_path?: string;
  content_md: string;
  channel_id?: string;
  tags?: string[];
  status: string;
  is_moc?: boolean;
  source_url?: string;
};

/** 草稿自动保存间隔(毫秒) */
const AUTOSAVE_DELAY = 5000;

/** 新建笔记自动创建延迟(毫秒) —— 比编辑自动保存短，尽快创建并跳转编辑页 */
const AUTOCREATE_DELAY = 2000;

/** 当前时间作为标题（YYYY-MM-DD HH:mm） */
function nowAsTitle(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** metaValues 初始值 */
const META_VALUES_INIT = {
  status: 'draft',
  channel_id: undefined as string | undefined,
  category: 'inbox',
  folder_path: '' as string,
  slug: '',
  tags: [] as string[],
  is_moc: false,
  source_url: '' as string,
  excerpt: '' as string,
};

/**
 * 知识库笔记编辑器（共用新建/编辑）。
 *
 * 三段式布局（参考 Notion / Obsidian）：
 * - 顶部条：返回 / 面包屑 / 保存状态 / META 按钮 / 状态徽章
 * - 写作区：占满宽度，hero 标题 + 全宽编辑器
 * - 底部条：字数 / 阅读 / 出链 / 反链 / 保存按钮
 *
 * 元信息（状态/频道/分类/Slug/Tags/MOC/来源/摘要/模板）收进顶部
 * META 抽屉浮层，写作时消失，按需展开。
 */
export default function NoteEditor({ note }: { note?: KbNote }) {
  const router = useRouter();
  const { message } = App.useApp();
  const [form] = Form.useForm<FormValues>();
  const isEdit = !!note;

  const slugTouchedRef = useRef(false);
  const metaTriggerRef = useRef<HTMLButtonElement>(null);

  // Refs 用于在异步回调（setTimeout/setTimeout 闭包）中获取最新 state
  const contentMdRef = useRef('');
  const titleValueRef = useRef('');
  const statusValueRef = useRef('draft');
  const metaValuesRef = useRef(META_VALUES_INIT);
  const categoryValueRef = useRef('inbox');
  const folderPathValueRef = useRef('');

  const [autoSaveStatus, setAutoSaveStatus] = useState<
    'idle' | 'pending' | 'saving' | 'saved'
  >('idle');
  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latestValuesRef = useRef<FormValues | null>(null);

  const [metaDrawerVisible, setMetaDrawerVisible] = useState(false);
  const [editorMode, setEditorMode] = useState<'split' | 'tab' | 'preview'>('split');

  // 实时内容（用于字数/出链统计）—— 用 state 而非 Form.useWatch，确保编辑器输入时触发重渲染
  const [contentMd, setContentMd] = useState('');
  const [titleValue, setTitleValue] = useState('');

  // MetaDrawer 需要的完整表单值（避免它在 render 阶段调 form.getFieldValue）
  // 必须在 useCallback/useMemo 之前定义，否则 TDZ 错误
  const [statusValue, setStatusValue] = useState('draft');
  const [categoryValue, setCategoryValue] = useState('inbox');
  const [folderPathValue, setFolderPathValue] = useState('');
  const [metaValues, setMetaValues] = useState(META_VALUES_INIT);

  // 同步 refs（在 render 阶段同步，确保异步回调能读到最新值）
  contentMdRef.current = contentMd;
  titleValueRef.current = titleValue;
  statusValueRef.current = statusValue;
  metaValuesRef.current = metaValues;
  categoryValueRef.current = categoryValue;
  folderPathValueRef.current = folderPathValue;

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
    // 同步到 state（用于实时统计和 UI 显示）
    setTitleValue(note.title);
    setContentMd(note.content_md);
    setStatusValue(note.status);
    setCategoryValue(note.category);
    setFolderPathValue(note.folder_path || '');
    setMetaValues({
      status: note.status,
      channel_id: note.channel_id || undefined,
      category: note.category,
      folder_path: note.folder_path || '',
      slug: note.slug,
      tags: note.tags || [],
      is_moc: note.is_moc,
      source_url: note.source_url || '',
      excerpt: note.excerpt || '',
    });
  }, [note, form]);

  // title 变化时自动生成 slug
  const handleTitleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const title = e.target.value;
      titleValueRef.current = title;
      setTitleValue(title);
      form.setFieldValue('title', title);
      if (!slugTouchedRef.current) {
        form.setFieldValue('slug', slugify(title));
      }
    },
    [form],
  );

  // 模板选择：填充 content_md
  const handleTemplate = useCallback(
    (templateId: string) => {
      const tpl = templates?.find((t) => t.id === templateId);
      if (!tpl) return;
      const current = contentMd || '';
      const today = new Date().toISOString().slice(0, 10);
      const filled = tpl.content_md
        .replace(/\{\{date\}\}/g, today)
        .replace(/\{\{title\}\}/g, titleValue || '')
        .replace(/\{\{topic\}\}/g, titleValue || '')
        .replace(/\{\{book_title\}\}/g, titleValue || '');
      const newContent = current + (current ? '\n\n' : '') + filled;
      setContentMd(newContent);
      form.setFieldValue('content_md', newContent);
      if (!form.getFieldValue('category')) {
        form.setFieldValue('category', tpl.category);
        setCategoryValue(tpl.category);
        setMetaValues((m) => ({ ...m, category: tpl.category }));
      }
      message.success(`已套用模板：${tpl.name}`);
      setMetaDrawerVisible(false);
    },
    [templates, form, message, contentMd, titleValue],
  );

  // 双链笔记搜索（供 MarkdownEditor 调用）
  const searchNotes = useCallback(async (q: string): Promise<WikilinkItem[]> => {
    const res = await kbApi.listNotes({ q: q || undefined, size: 10 });
    return res.items.map((i) => ({ id: i.id, title: i.title }));
  }, []);

  // 草稿自动保存 / 新建自动创建（从 ref 读取最新 state，避免闭包陷阱）
  const triggerAutoSave = useCallback(
    () => {
      if (autoSaveStatus === 'saving') return;

      // 新建模式：用户输入正文后自动创建（标题为空则用当前时间）
      if (!isEdit) {
        // 只有正文非空才触发自动创建，避免空笔记
        if (!contentMdRef.current?.trim()) return;
        if (statusValueRef.current !== 'draft') return;

        setAutoSaveStatus('pending');

        if (autoSaveTimerRef.current) {
          clearTimeout(autoSaveTimerRef.current);
        }
        autoSaveTimerRef.current = setTimeout(async () => {
          setAutoSaveStatus('saving');
          const mv = metaValuesRef.current;
          const title = titleValueRef.current?.trim() || nowAsTitle();
          const slug = slugTouchedRef.current
            ? (form.getFieldValue('slug') || slugify(title))
            : slugify(title);
          const payload: KbNoteCreatePayload = {
            slug,
            title,
            excerpt: mv.excerpt || null,
            category: categoryValueRef.current || 'inbox',
            folder_path: folderPathValueRef.current || null,
            content_md: contentMdRef.current,
            channel_id: mv.channel_id || null,
            tags: mv.tags?.length ? mv.tags : null,
            status: statusValueRef.current || 'draft',
            is_moc: mv.is_moc || false,
            source_url: mv.source_url || null,
          };
          try {
            await createNote.mutateAsync(payload);
            // onSuccess 会跳转到编辑页
          } catch {
            setAutoSaveStatus('idle');
          }
        }, AUTOCREATE_DELAY);
        return;
      }

      // 编辑模式：草稿自动保存
      if (!note) return;
      if (statusValueRef.current !== 'draft') return;

      setAutoSaveStatus('pending');

      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
      autoSaveTimerRef.current = setTimeout(async () => {
        if (!note) return;
        setAutoSaveStatus('saving');
        const mv = metaValuesRef.current;
        const title = titleValueRef.current?.trim() || nowAsTitle();
        const slug = slugTouchedRef.current
          ? (form.getFieldValue('slug') || slugify(title))
          : slugify(title);
        const payload: KbNoteUpdatePayload = {
          slug,
          title,
          excerpt: mv.excerpt || null,
          category: categoryValueRef.current || 'inbox',
          folder_path: folderPathValueRef.current || null,
          content_md: contentMdRef.current,
          tags: mv.tags?.length ? mv.tags : null,
          status: statusValueRef.current,
          is_moc: mv.is_moc || false,
          source_url: mv.source_url || null,
        };
        try {
          await updateNote.mutateAsync({ id: note.id, payload });
          setAutoSaveStatus('saved');
        } catch {
          setAutoSaveStatus('idle');
        }
      }, AUTOSAVE_DELAY);
    },
    [isEdit, note, autoSaveStatus, updateNote, createNote, form],
  );

  useEffect(() => {
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, []);

  /** 从 state 直接构造创建/更新 payload（标题为空时用当前时间，不依赖 form.getFieldsValue） */
  const buildPayloadFromState = useCallback(() => {
    const title = titleValue?.trim() || nowAsTitle();
    const slug = slugTouchedRef.current
      ? (form.getFieldValue('slug') || slugify(title))
      : slugify(title);
    const tags = metaValues.tags?.length ? metaValues.tags : null;
    const channelId =
      statusValue === 'published' ? metaValues.channel_id : metaValues.channel_id || null;
    return { title, slug, tags, channelId };
  }, [titleValue, form, metaValues, statusValue]);

  const onFinish = (values: FormValues) => {
    // 保留 form.submit() 入口（隐藏的 submit 按钮），但实际逻辑由 handleSubmit 直接处理
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
  };

  const submitting = createNote.isPending || updateNote.isPending;

  // 提交前处理：标题为空用当前时间，直接调用 mutation（用 state 构造 payload，绕过 form 链路）
  const handleSubmit = useCallback(() => {
    const { title, slug, tags, channelId } = buildPayloadFromState();
    // 注意：不在 handleSubmit 中调用 setTitleValue，避免重渲染干扰 mutate
    if (statusValue === 'published' && !metaValues.channel_id) {
      message.error('发布到博客必须选择频道（在 META 面板中设置）');
      setMetaDrawerVisible(true);
      return;
    }
    if (isEdit && note) {
      const payload: KbNoteUpdatePayload = {
        slug,
        title,
        excerpt: metaValues.excerpt || null,
        category: categoryValue || 'inbox',
        folder_path: folderPathValue || null,
        content_md: contentMd || '',
        channel_id: channelId,
        tags,
        status: statusValue || 'draft',
        is_moc: metaValues.is_moc || false,
        source_url: metaValues.source_url || null,
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
        slug,
        title,
        excerpt: metaValues.excerpt || null,
        category: categoryValue || 'inbox',
        folder_path: folderPathValue || null,
        content_md: contentMd || '',
        channel_id: channelId,
        tags,
        status: statusValue || 'draft',
        is_moc: metaValues.is_moc || false,
        source_url: metaValues.source_url || null,
      };
      createNote.mutate(payload);
    }
  }, [buildPayloadFromState, statusValue, metaValues, message,
      isEdit, note, categoryValue, folderPathValue, contentMd,
      createNote, updateNote]);

  // ===== 实时统计 =====
  const stats = useMemo(() => {
    const text = contentMd || '';
    // 字数：中文按字，英文按词
    const cjk = (text.match(/[\u4e00-\u9fff]/g) || []).length;
    const en = (text.match(/[a-zA-Z]+/g) || []).length;
    const wordCount = cjk + en;
    // 阅读时长：中文 300 字/分，英文 200 词/分
    const readingTime = Math.max(1, Math.ceil(cjk / 300 + en / 200));
    // 出链数（[[xxx]] 且非 ![[）
    const outlinks = (text.match(/(?<!!)\[\[[^\]]+\]\]/g) || []).length;
    return { wordCount, readingTime, outlinks };
  }, [contentMd]);

  const backlinksCount = backlinks?.length || 0;

  // 面包屑分类映射
  const categoryLabel = useMemo(() => {
    const map: Record<string, string> = {
      inbox: '00_Inbox',
      daily: '01_Daily',
      reading: '02_Reading',
      knowledge: '03_Knowledge',
      projects: '04_Projects',
      templates: '05_Templates',
      assets: '06_Assets',
    };
    return map[categoryValue] || categoryValue;
  }, [categoryValue]);

  /** 统一字段变化处理：Form.onValuesChange 和 MetaDrawer.onFieldChange 共用 */
  const handleFieldChange = useCallback((field: string, value: unknown) => {
    switch (field) {
      case 'status':
        setStatusValue((value as string) || 'draft');
        setMetaValues((m) => ({ ...m, status: (value as string) || 'draft' }));
        break;
      case 'category':
        setCategoryValue((value as string) || 'inbox');
        setMetaValues((m) => ({ ...m, category: (value as string) || 'inbox' }));
        break;
      case 'folder_path':
        setFolderPathValue((value as string) || '');
        setMetaValues((m) => ({ ...m, folder_path: (value as string) || '' }));
        break;
      case 'content_md':
        setContentMd((value as string) || '');
        break;
      case 'title':
        setTitleValue((value as string) || '');
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
      case 'is_moc':
        setMetaValues((m) => ({ ...m, is_moc: (value as boolean) || false }));
        break;
      case 'source_url':
        setMetaValues((m) => ({ ...m, source_url: (value as string) || '' }));
        break;
      case 'excerpt':
        setMetaValues((m) => ({ ...m, excerpt: (value as string) || '' }));
        break;
    }
  }, []);

  /** Form.onValuesChange：遍历 changed 字段逐一同步 */
  const onValuesChangeHandler = useCallback(
    (changed: Partial<FormValues>, _allValues: FormValues) => {
      for (const field of Object.keys(changed) as (keyof FormValues)[]) {
        handleFieldChange(field, changed[field]);
      }
    },
    [handleFieldChange],
  );

  return (
    <Form<FormValues>
      form={form}
      layout="vertical"
      onFinish={onFinish}
      onValuesChange={onValuesChangeHandler}
      initialValues={{
        status: 'draft',
        category: 'inbox',
      }}
      requiredMark={false}
    >
      <EditorShell
        topBar={
          <>
            {/* ===== 左侧：返回 + 面包屑 ===== */}
            <div className="flex items-center gap-3">
              <Link
                href="/admin/knowledge"
                className="text-on-surface-variant hover:text-primary transition-colors"
              >
                <ArrowLeft size={16} />
              </Link>
              <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
                知识库
                <span className="text-outline-variant mx-1">/</span>
                <span className="text-on-surface">
                  {isEdit ? note?.slug : '新建笔记'}
                </span>
              </span>
            </div>

            {/* ===== 右侧：保存状态 / META / 状态徽章 / 主操作 ===== */}
            <div className="relative flex items-center gap-3">
              {/* 保存状态 */}
              {autoSaveStatus !== 'idle' && (
                <span className="font-mono text-label-mono uppercase tracking-widest flex items-center gap-1">
                  {autoSaveStatus === 'pending' && (
                    <span className="text-tertiary-fixed">
                      {isEdit ? '编辑中…' : '待创建…'}
                    </span>
                  )}
                  {autoSaveStatus === 'saving' && (
                    <span className="text-tertiary-fixed">
                      {isEdit ? '保存中…' : '创建中…'}
                    </span>
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
                    : statusValue === 'private'
                    ? 'border-outline text-on-surface-variant'
                    : 'border-outline-variant text-on-surface-variant'
                }`}
              >
                {statusValue === 'published'
                  ? 'PUBLISHED'
                  : statusValue === 'private'
                  ? 'PRIVATE'
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
              <MetaDrawer
                visible={metaDrawerVisible}
                onClose={() => setMetaDrawerVisible(false)}
                form={form}
                values={metaValues}
                onFieldChange={handleFieldChange}
                channels={channelsData?.items || []}
                channelsLoading={channelsLoading}
                templates={templates?.map((t) => ({
                  id: t.id,
                  name: t.name,
                  category: t.category,
                }))}
                onTemplateSelect={handleTemplate}
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
            backlinksCount={backlinksCount}
            autoSaveStatus={autoSaveStatus}
            isEdit={isEdit}
          />
        }
      >
        {/* ===== 写作区（占满宽度）===== */}
        <div className="w-full px-6 lg:px-10 xl:px-14 py-6">
          {/* Hero 标题（不通过 Form.Item 包裹，自定义绑定）*/}
          <input
            type="text"
            placeholder="无标题笔记"
            value={titleValue}
            onChange={handleTitleChange}
            className="w-full bg-transparent border-none outline-none font-headline text-[28px] font-semibold text-primary leading-tight tracking-tighter placeholder:text-outline-variant focus:outline-none pb-1 border-b border-transparent focus:border-outline-variant transition-colors mb-3"
          />

          {/* 标题下方元信息（日期/分类/子目录） */}
          <div className="flex items-center gap-2 font-mono text-label-mono text-on-surface-variant uppercase tracking-widest mb-6">
            <span>
              {isEdit && note?.updated_at
                ? new Date(note.updated_at).toLocaleDateString('zh-CN')
                : new Date().toLocaleDateString('zh-CN')}
            </span>
            <span className="w-1 h-1 bg-outline-variant" />
            <span>{categoryLabel}</span>
            {folderPathValue && (
              <>
                <span className="w-1 h-1 bg-outline-variant" />
                <span className="text-tertiary-fixed">{folderPathValue}</span>
              </>
            )}
            {titleValue && !slugTouchedRef.current && (
              <>
                <span className="w-1 h-1 bg-outline-variant" />
                <span className="text-tertiary-fixed/70">slug: {slugify(titleValue)}</span>
              </>
            )}
          </div>

          {/* 全宽编辑器（不通过 Form.Item 包裹，避免 onChange 冲突）*/}
          <MarkdownEditor
            value={contentMd}
            onChange={(val) => {
              contentMdRef.current = val;
              setContentMd(val);
              form.setFieldValue('content_md', val);
              triggerAutoSave();
            }}
            placeholder="## 开始书写&#10;&#10;支持 [[双链]]、#标签、GFM、代码高亮、数学公式、Mermaid&#10;&#10;粘贴或拖拽图片自动上传"
            enableWikilink
            searchNotes={searchNotes}
            excludeNoteId={note?.id}
            mode={editorMode}
            onModeChange={setEditorMode}
          />
        </div>
      </EditorShell>

      <button type="submit" className="hidden" aria-hidden />
    </Form>
  );
}
