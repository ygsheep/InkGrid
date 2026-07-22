'use client';

import { useParams } from 'next/navigation';
import { Alert, Spin } from 'antd';
import PostEditor from '@/components/admin/PostEditor';
import { useAdminPost } from '@/hooks/useAdmin';

export default function EditPostPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const { data: post, isLoading, error } = useAdminPost(id);

  if (!id) {
    return <Alert type="error" message="缺少文章 ID" showIcon />;
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        type="error"
        message="加载失败"
        description={error.message}
        showIcon
      />
    );
  }

  if (!post) {
    return <Alert type="warning" message="文章不存在" showIcon />;
  }

  return <PostEditor post={post} />;
}
