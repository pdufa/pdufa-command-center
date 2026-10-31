import "./globals.css";
import GlobalNavigation from "./GlobalNavigation";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "PDUFA Command Center — New Platform Setup",
  description: "Isolated Next.js + FastAPI test platform. Streamlit remains untouched."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en"><body><GlobalNavigation />{children}</body></html>
  );
}
