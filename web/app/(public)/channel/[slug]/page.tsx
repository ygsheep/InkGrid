import { redirect } from 'next/navigation';

/**
 * 旧路由 /channel/[slug] 已废弃,统一重定向到 /channel?channel=slug。
 * 频道切换现已聚合到 /channel 单页内通过横向 chips 完成,不再每个频道一个页面。
 * 保留 tag 参数以兼容旧链接的标签筛选状态。
 */
export default async function ChannelSlugRedirect({
  params,
  searchParams,
}: {
  params: { slug: string };
  searchParams: { tag?: string };
}) {
  const target = new URLSearchParams({ channel: params.slug });
  if (searchParams.tag) target.set('tag', searchParams.tag);
  redirect(`/channel?${target.toString()}`);
}
