import { Check, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { NotificationDto } from "@/features/notifications/api";
import {
  formatRelativeTime,
  notificationIcon,
} from "@/features/notifications/format";
import { cn } from "@/lib/utils";

interface NotificationItemProps {
  notification: NotificationDto;
  /** Called when the user marks this notification read. Omit to hide the action. */
  onMarkRead?: (id: number) => void;
  /** Called to deliver this notification to Telegram. Omit to hide the action. */
  onSend?: (id: number) => void;
  /** Whether Telegram delivery is available (controls the send action). */
  canSend?: boolean;
  /** Disable the actions while a mutation is in flight. */
  busy?: boolean;
}

/** A single notification row: icon, title/body, relative time, unread state. */
export function NotificationItem({
  notification,
  onMarkRead,
  onSend,
  canSend = false,
  busy = false,
}: NotificationItemProps) {
  const Icon = notificationIcon(notification);
  const unread = !notification.is_read;
  const showSend = canSend && onSend && !notification.is_delivered;

  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-md border border-border p-3 transition-colors",
        unread ? "bg-accent/40" : "bg-background",
      )}
    >
      <div className="relative mt-0.5 shrink-0">
        <Icon
          className={cn(
            "h-4 w-4",
            notification.priority === "high"
              ? "text-destructive"
              : "text-muted-foreground",
          )}
        />
        {unread && (
          <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-primary" />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <p
            className={cn(
              "truncate text-sm",
              unread ? "font-semibold" : "font-medium",
            )}
          >
            {notification.title}
          </p>
          <span className="shrink-0 text-xs text-muted-foreground">
            {formatRelativeTime(notification.created_at)}
          </span>
        </div>
        {notification.body && (
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {notification.body}
          </p>
        )}
        {notification.is_delivered && (
          <span className="mt-1 inline-flex items-center gap-1 text-[11px] text-muted-foreground">
            <Send className="h-3 w-3" />
            Sent to Telegram
          </span>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-1">
        {showSend && (
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            disabled={busy}
            aria-label="Send to Telegram"
            title="Send to Telegram"
            onClick={() => onSend(notification.id)}
          >
            <Send className="h-4 w-4" />
          </Button>
        )}
        {unread && onMarkRead && (
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            disabled={busy}
            aria-label="Mark as read"
            title="Mark as read"
            onClick={() => onMarkRead(notification.id)}
          >
            <Check className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
