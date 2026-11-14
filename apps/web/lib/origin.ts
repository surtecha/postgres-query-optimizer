/** Compare browser origins with the HTTP authority, not the server bind address. */
export function isSameOrigin(
  origin: string | null,
  host: string | null,
  protocol: string,
): boolean {
  // Non-browser clients do not necessarily send Origin. Bearer authentication
  // remains enforced upstream, and no cookie credentials are added by this proxy.
  if (origin === null) return true;
  if (!host || !["http:", "https:"].includes(protocol)) return false;
  try {
    const expected = new URL(`${protocol}//${host}`);
    const supplied = new URL(origin);
    if (expected.username || expected.password || expected.pathname !== "/" ||
        expected.search || expected.hash) return false;
    return supplied.origin === origin && supplied.origin === expected.origin;
  } catch {
    return false;
  }
}
