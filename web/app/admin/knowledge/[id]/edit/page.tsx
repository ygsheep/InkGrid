'use client';

import { useParams } from 'next/navigation';
import { Alert, Spin } from 'antd';
import { useKbNote } from '@/hooks/useAdmin';
import NoteEditor from '@/components/admin/NoteEditor';

export default function EditNotePage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const { data: note, isLoading, isError, error } = useKbNote(id);

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spin size="large" />
      </div>
    );
  }

  if (isError) {
    return (
      <Alert
        type="error"
        message="加载失败"
        description={error?.message || '笔记不存在或无权访问'}
        showIcon
      />
    );
  }

  if (!note) {
    return <Alert type="warning" message="笔记不存在" showIcon />;
  }

  return <NoteEditor note={note} />;
}
