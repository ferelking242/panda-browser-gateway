"use client"

import * as React from "react"
import {
  LayoutDashboard,
  Activity,
  Settings,
  Terminal,
  MessageSquare,
  Image,
  ScrollText,
  SlidersHorizontal,
  PawPrint,
  MonitorPlay,
  MessageCircle,
} from "lucide-react"
import Link from "next/link"
import { SidebarNotification } from "@/components/sidebar-notification"
import { NavMain } from "@/components/nav-main"
import { NavUser } from "@/components/nav-user"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

const data = {
  user: {
    name: "Gateway Admin",
    email: "local · port 8000",
    avatar: "",
  },
  navGroups: [
    {
      label: "Monitor",
      items: [
        { title: "Overview",  url: "/dashboard",  icon: LayoutDashboard },
        { title: "Client",    url: "/client",     icon: MessageCircle },
        { title: "Browser",   url: "/browser",    icon: MonitorPlay },
        { title: "Requests",  url: "/requests",   icon: Activity },
        { title: "Threads",   url: "/threads",    icon: MessageSquare },
        { title: "Images",    url: "/images",     icon: Image },
        { title: "Logs",      url: "/logs",       icon: ScrollText },
      ],
    },
    {
      label: "Manage",
      items: [
        { title: "Configuration", url: "/config",    icon: Settings },
        { title: "API Docs",      url: "/api-docs",  icon: Terminal },
        { title: "Settings",      url: "/settings",  icon: SlidersHorizontal },
      ],
    },
  ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/dashboard">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <PawPrint size={18} />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">Panda Gateway</span>
                  <span className="truncate text-xs text-muted-foreground">Browser AI API</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        {data.navGroups.map((group) => (
          <NavMain key={group.label} label={group.label} items={group.items} />
        ))}
      </SidebarContent>
      <SidebarFooter>
        <SidebarNotification />
        <NavUser user={data.user} />
      </SidebarFooter>
    </Sidebar>
  )
}
