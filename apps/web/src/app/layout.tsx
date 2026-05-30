import type { Metadata } from "next";

import "antd/dist/reset.css";
import "./styles.css";

export const metadata: Metadata = {
  title: "TripOS",
  description: "Payments and operations for paid group trips"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
