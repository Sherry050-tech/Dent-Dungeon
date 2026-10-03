// app/design/page.tsx  (temporary: delete before merging, or keep dev-only)
import { notFound } from "next/navigation";
import { CalendarDays, Users, Wallet, Receipt } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Logo } from "@/components/layout/logo";
import { PageHeader } from "@/components/layout/page-header";
import { StatCard } from "@/components/ui/stat-card";
import { StatusBadge, type BadgeStatus } from "@/components/ui/status-badge";
import { EmptyState } from "@/components/ui/empty-state";

const BADGES: BadgeStatus[] = [
  "scheduled", "confirmed", "in_progress", "completed", "cancelled",
  "no_show", "pending", "active", "admin", "doctor", "receptionist",
];

export default function DesignPreview() {
  if (process.env.NODE_ENV === "production") notFound();

  return (
    <main className="mx-auto max-w-7xl space-y-8 p-6">
      <Logo />
      <PageHeader
        title="Design preview"
        subtitle="Every shared component in the Dent-Dungeon theme."
        actions={<Button>Primary action</Button>}
      />

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Buttons</h2>
        <div className="flex flex-wrap gap-2">
          <Button>Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="destructive">Destructive</Button>
          <Button disabled>Disabled</Button>
        </div>
      </section>

      <section className="max-w-sm space-y-2">
        <h2 className="text-lg font-semibold">Input</h2>
        <Label htmlFor="email">Email</Label>
        <Input id="email" placeholder="sara@clinic.com" />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Badges</h2>
        <div className="flex flex-wrap gap-2">
          {BADGES.map((b) => (
            <StatusBadge key={b} status={b} />
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Stat cards</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Today's appointments" value={12} icon={CalendarDays} note="5 completed" noteTone="success" />
          <StatCard label="New patients" value={2} icon={Users} />
          <StatCard label="Revenue today" value="45,000" icon={Wallet} note="PKR" />
          <StatCard label="Outstanding" value="130,000" icon={Receipt} note="PKR" />
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Empty state</h2>
        <EmptyState
          icon={Users}
          title="No patients yet"
          description="Patient records will appear here."
          action={<Button>Add patient</Button>}
        />
      </section>
    </main>
  );
}
