import { NextRequest, NextResponse } from 'next/server';
import { revalidatePath, revalidateTag } from 'next/cache';

/**
 * On-demand revalidate endpoint.
 * 后端在文章 CRUD 后 POST 此端点，让 Next.js 重新生成受影响页面。
 *
 * Body: { secret: string, paths: string[], tags: string[] }
 *
 * secret 与 .env 的 REVALIDATE_SECRET 比对。
 */
export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  if (!body || typeof body !== 'object') {
    return NextResponse.json({ ok: false, message: 'invalid body' }, { status: 400 });
  }

  const secret = body.secret as string | undefined;
  const expected = process.env.REVALIDATE_SECRET;
  if (!expected || secret !== expected) {
    return NextResponse.json({ ok: false, message: 'unauthorized' }, { status: 401 });
  }

  const paths = Array.isArray(body.paths) ? (body.paths as string[]) : [];
  const tags = Array.isArray(body.tags) ? (body.tags as string[]) : [];

  let invalidated = 0;
  for (const tag of tags) {
    revalidateTag(tag);
    invalidated++;
  }
  for (const path of paths) {
    revalidatePath(path);
    invalidated++;
  }

  return NextResponse.json({ ok: true, invalidated, paths, tags });
}

export async function GET() {
  return NextResponse.json({ ok: false, message: 'POST only' }, { status: 405 });
}
