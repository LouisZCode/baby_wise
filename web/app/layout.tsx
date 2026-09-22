import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "bby_wise",
  description: "Baby-health Q&A for everyday questions",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="de">
      <body className="bg-stone-50 text-stone-900 antialiased">
        {children}
      </body>
    </html>
  );
}
