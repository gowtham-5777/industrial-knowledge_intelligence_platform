import type { LucideIcon } from "lucide-react";
import {
  Activity,
  BookOpen,
  Cloud,
  Compass,
  FileText,
  Gauge,
  GitBranch,
  LayoutDashboard,
  MessageSquare,
  Search,
  Settings,
  ShieldCheck,
  Wrench,
} from "lucide-react";

export type NavItem = {
  title: string;
  href: string;
  icon: LucideIcon;
  description: string;
  primary?: boolean;
};

/** Architecture §10 — Enterprise Navigation (Primary Sidebar) */
export const PRIMARY_NAV: NavItem[] = [
  {
    title: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
    description: "Fleet KPIs, indexing status, and alerts.",
  },
  {
    title: "Industrial Copilot",
    href: "/copilot",
    icon: MessageSquare,
    description: "Global motor-aware Q&A with citations.",
  },
  {
    title: "Motor Explorer",
    href: "/motors",
    icon: Compass,
    description: "Primary entry — browse and filter motors.",
    primary: true,
  },
  {
    title: "Knowledge Graph",
    href: "/graph",
    icon: GitBranch,
    description: "Motor-centered knowledge graph view.",
  },
  {
    title: "Drawing Explorer",
    href: "/drawings",
    icon: FileText,
    description: "Drawing-number cross-reference.",
  },
  {
    title: "Maintenance Intelligence",
    href: "/maintenance",
    icon: Wrench,
    description: "Test metrics and anomaly patterns.",
  },
  {
    title: "Compliance Center",
    href: "/compliance",
    icon: ShieldCheck,
    description: "Regulation and certification coverage.",
  },
  {
    title: "AI Search",
    href: "/search",
    icon: Search,
    description: "Unified semantic, motor, and drawing search.",
  },
  {
    title: "Analytics",
    href: "/analytics",
    icon: Gauge,
    description: "Fleet stats, indexing trends, domain coverage.",
  },
  {
    title: "Document Library",
    href: "/documents",
    icon: BookOpen,
    description: "Secondary document catalog for power users.",
  },
  {
    title: "Google Drive Sync",
    href: "/sync",
    icon: Cloud,
    description: "Continuous Intelligent Indexing status.",
  },
  {
    title: "Administration",
    href: "/admin",
    icon: Settings,
    description: "Users, roles, and audit events.",
  },
];

export const MOTOR_360_HINT = {
  title: "Motor 360",
  hrefPattern: "/motors/[id]",
  icon: Activity,
  description: "Flagship asset command center — open a motor from Explorer.",
};
