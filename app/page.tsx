import type { Metadata } from "next";
import analytics from "../data/corridor_analytics.json";
import Dashboard from "./dashboard";

export const metadata: Metadata = {
  title: "LunarBank · Remittance Cost Intelligence",
  description: "Cross-border cost intelligence and routing recommendations for LunarBank operations.",
};

export default function Home() {
  return <Dashboard data={analytics} />;
}
