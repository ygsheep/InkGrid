'use client';

import { Input, Button, Form } from 'antd';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense } from 'react';

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get('redirect') || '/admin';
  const siteName = (process.env.NEXT_PUBLIC_SITE_NAME || 'inkgrid.dev').toUpperCase();

  const onFinish = () => {
    // 骨架阶段写 mock cookie，生产由后端 Set-Cookie httpOnly
    document.cookie = 'admin_token=mock; path=/';
    router.push(redirect);
  };

  return (
    <div className="w-full max-w-sm border border-outline-variant bg-surface-container-lowest p-8">
      <h1 className="font-mono text-label-mono text-primary mb-2 text-center uppercase tracking-widest">
        {siteName}
      </h1>
      <p className="font-mono text-label-mono text-on-surface-variant text-center mb-8 uppercase tracking-widest">
        登录管理后台
      </p>
      <Form layout="vertical" onFinish={onFinish} requiredMark={false}>
        <Form.Item
          name="username"
          label={
            <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
              用户名
            </span>
          }
        >
          <Input size="large" placeholder="请输入用户名" />
        </Form.Item>
        <Form.Item
          name="password"
          label={
            <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
              密码
            </span>
          }
        >
          <Input.Password size="large" placeholder="请输入密码" />
        </Form.Item>
        <Button
          type="primary"
          htmlType="submit"
          size="large"
          block
          className="mt-2"
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
