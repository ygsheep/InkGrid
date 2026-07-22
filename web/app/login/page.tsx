'use client';

import { useState } from 'react';
import { Input, Button, Form, App } from 'antd';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { useLogin } from '@/hooks/useAdmin';

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get('redirect') || '/admin';
  const siteName = (process.env.NEXT_PUBLIC_SITE_NAME || 'inkgrid.dev').toUpperCase();
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  // 监听用户名/密码字段值，两者都有值时按钮启用主色背景
  const username = Form.useWatch('username', form);
  const password = Form.useWatch('password', form);
  const canSubmit = Boolean(username && password);

  const login = useLogin({
    onSuccess: () => {
      message.success('登录成功');
      // 不调用 router.refresh()：push 触发的客户端导航会让 middleware
      // 在 RSC 请求上重新运行并读取最新 cookie，refresh 反而会与 push 竞态。
      router.push(redirect);
    },
    onError: (err) => {
      message.error(err.message || '登录失败');
    },
  });

  const onFinish = (values: { username: string; password: string }) => {
    setLoading(true);
    login.mutate(values, {
      onSettled: () => setLoading(false),
    });
  };

  return (
    <div className="w-full max-w-sm border border-outline-variant bg-surface-container-lowest p-8">
      <h1 className="font-mono text-label-mono text-primary mb-2 text-center uppercase tracking-widest">
        {siteName}
      </h1>
      <p className="font-mono text-label-mono text-on-surface-variant text-center mb-8 uppercase tracking-widest">
        登录管理后台
      </p>
      <Form
        form={form}
        layout="vertical"
        onFinish={onFinish}
        requiredMark={false}
      >
        <Form.Item
          name="username"
          label={
            <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
              用户名
            </span>
          }
          rules={[{ required: true, message: '请输入用户名' }]}
        >
          <Input size="large" placeholder="请输入用户名" autoComplete="username" />
        </Form.Item>
        <Form.Item
          name="password"
          label={
            <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
              密码
            </span>
          }
          rules={[{ required: true, message: '请输入密码' }]}
        >
          <Input.Password
            size="large"
            placeholder="请输入密码"
            autoComplete="current-password"
          />
        </Form.Item>
        <Button
          type="primary"
          htmlType="submit"
          size="large"
          block
          className={`mt-2 transition-colors ${
            canSubmit
              ? '!bg-primary !text-on-primary hover:!bg-primary-fixed'
              : ''
          }`}
          loading={loading}
        >
          登录
        </Button>
      </Form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="spatial-grid min-h-screen flex items-center justify-center px-margin-mobile">
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
