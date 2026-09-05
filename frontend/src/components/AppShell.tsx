import { useState, type ReactNode } from "react";
import { MessageSquare } from "lucide-react";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { AssistantPanel } from "./AssistantPanel";

export function AppShell({ children }: { children: ReactNode }) {
  const [navOpen, setNavOpen] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <div className="hidden w-[240px] shrink-0 lg:block">
        <Sidebar />
      </div>

      <Sheet open={navOpen} onOpenChange={setNavOpen}>
        <SheetContent side="left" className="w-[260px] border-sidebar-border p-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <Sidebar onNavigate={() => setNavOpen(false)} />
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <Header onOpenMenu={() => setNavOpen(true)} />
        <main className="min-h-0 flex-1 overflow-y-auto px-4 py-4 md:px-6">{children}</main>
      </div>

      <div className="hidden w-[340px] shrink-0 xl:block">
        <AssistantPanel />
      </div>

      <Button
        onClick={() => setAssistantOpen(true)}
        className="fixed right-4 bottom-4 z-40 gap-2 rounded-full shadow-lg xl:hidden"
      >
        <MessageSquare className="size-4" />
        Ask ORCA
      </Button>

      <Sheet open={assistantOpen} onOpenChange={setAssistantOpen}>
        <SheetContent
          side="right"
          className="w-full border-border bg-card p-0 sm:max-w-[380px]"
        >
          <SheetTitle className="sr-only">ORCA AI Assistant</SheetTitle>
          <AssistantPanel />
        </SheetContent>
      </Sheet>
    </div>
  );
}
