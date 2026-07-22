'use client';

import { useEffect, useState } from 'react';
import { Alert, App, Button, Form, Input, Spin } from 'antd';
import { Save } from 'lucide-react';
import {
  useAdminSettings,
  useUpdateSettings,
} from '@/hooks/useAdmin';
import type { SettingsUpdatePayload } from '@/lib/api/admin';

type FormValues = {
  site_name: string;
  author: string;
  version: string;
  extra_json: string; // JSON 字符串，方便编辑
};

function fieldLabel(text: string) {
  return (
    <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
      {text}
    </span>
  );
}

export default function AdminSettingsPage() {
  const { message } = App.useApp();
  const [form] = Form.useForm<FormValues>();
  const [extraError, setExtraError] = useState<string | null>(null);

  const { data, isLoading, error } = useAdminSettings();
  const updateSettings = useUpdateSettings({
    onSuccess: () => message.success('已保存'),
    onError: (e) => message.error(e.message),
  });

  useEffect(() => {
    if (!data) return;
    form.setFieldsValue({
      site_name: data.siteName,
      author: data.author,
      version: data.version,
      extra_json: JSON.stringify(data.extra || {}, null, 2),
    });
  }, [data, form]);

  const onSubmit = (values: FormValues) => {
    setExtraError(null);
    let extra: Record<string, unknown> = {};
    if (values.extra_json.trim()) {
      try {
        const parsed = JSON.parse(values.extra_json);
        if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
          setExtraError('extra 必须是 JSON 对象');
          return;
        }
        extra = parsed as Record<string, unknown>;
      } catch (e) {
        setExtraError('JSON 格式错误：' + (e as Error).message);
        return;
      }
    }
    const payload: SettingsUpdatePayload = {
      site_name: values.site_name,
      author: values.author,
      version: values.version,
      extra,
    };
    updateSettings.mutate(payload);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert type="error" message="加载失败" description={error.message} showIcon />
    );
  }

  return (
    <div>
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
            站点设置
          </h1>
          <p className="font-mono text-label-mono text-on-surface-variant mt-2 uppercase tracking-widest">
            SETTINGS · 站点名 / 署名 / 版本 / 扩展
          </p>
        </div>
        <Button
          type="primary"
          icon={<Save size={14} />}
          onClick={() => form.submit()}
          loading={updateSettings.isPending}
        >
          保存
        </Button>
      </div>

      <div className="max-w-2xl">
        <Form<FormValues>
          form={form}
          layout="vertical"
          onFinish={onSubmit}
          requiredMark={false}
        >
          <Form.Item
            name="site_name"
            label={fieldLabel('站点名')}
            rules={[{ required: true, message: '请输入站点名' }]}
          >
            <Input placeholder="inkgrid.dev" />
          </Form.Item>
          <Form.Item
            name="author"
            label={fieldLabel('署名')}
            rules={[{ required: true, message: '请输入署名' }]}
          >
            <Input placeholder="博主" />
          </Form.Item>
          <Form.Item
            name="version"
            label={fieldLabel('版本号')}
            rules={[{ required: true, message: '请输入版本号' }]}
          >
            <Input placeholder="v1.0.0" />
          </Form.Item>
          <Form.Item
            name="extra_json"
            label={fieldLabel('扩展配置 (JSON)')}
            validateStatus={extraError ? 'error' : undefined}
            help={
              extraError ? (
                <span className="text-error">{extraError}</span>
              ) : (
                <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
                  自由结构 JSON 对象，存放 SEO / 社交链接等
                </span>
              )
            }
          >
            <Input.TextArea
              autoSize={{ minRows: 8, maxRows: 20 }}
              className="font-mono"
              style={{ fontFamily: 'var(--font-jetbrains), monospace' }}
              placeholder='{"og_image": "/og.png", "social": {"twitter": "@"}}'
            />
          </Form.Item>

          <button type="submit" className="hidden" aria-hidden />
        </Form>
      </div>
    </div>
  );
}
