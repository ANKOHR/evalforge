import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EvalForge | AI evaluation regression gates",
  description: "Regression testing for LLM, RAG and agent systems.",
  openGraph: {
    title: "EvalForge",
    description: "Quality gates for AI systems.",
    type: "website",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
