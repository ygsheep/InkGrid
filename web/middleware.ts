import { NextResponse, type NextRequest } from 'next/server';

/**
 * 鉴权中间件：拦截 /admin/*，未登录跳登录页。
 * token 存 httpOnly cookie（生产由后端 Set-Cookie，骨架阶段登录页写 mock）。
 */
export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (pathname.startsWith('/admin')) {
    const token = req.cookies.get('admin_token');
    if (!token) {
      const url = req.nextUrl.clone();
      url.pathname = '/login';
      url.searchParams.set('redirect', pathname);
      return NextResponse.redirect(url);
    }
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/admin/:path*'],
};
