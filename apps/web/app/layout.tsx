import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {title:"PostgreSQL Query Performance Engineer", description:"Controlled SQL experiments with measured acceptance"};
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>) {
 return <html lang="en"><body>{children}</body></html>;
}
