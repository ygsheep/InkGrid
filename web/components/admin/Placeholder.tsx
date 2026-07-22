/** 后台子页面占位（接入后端后替换为真实功能） */
export default function AdminPlaceholder({
  title,
  desc,
}: {
  title: string;
  desc?: string;
}) {
  return (
    <div>
      <h1 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
        {title}
      </h1>
      <p className="font-mono text-label-mono text-on-surface-variant mt-2 mb-12 uppercase tracking-widest">
        {desc || '建设中'}
      </p>
      <div className="border border-dashed border-outline-variant bg-surface-container-lowest py-20 text-center font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
        待接入后端
      </div>
    </div>
  );
}
