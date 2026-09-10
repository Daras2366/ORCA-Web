/**
 * AuthModal.tsx — Login / Register / Continue as Guest dialog.
 *
 * Uses the existing ORCA design system (shadcn Dialog, Tabs, Input, Button,
 * Select) and deep-ocean CSS variables. No new color tokens are introduced.
 */

import { useState } from "react";
import { Eye, EyeOff, Fish, Lock, Mail, User, Users } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

import { useAuth } from "@/hooks/useAuth";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const USER_TYPES = [
  { value: "fisherman", label: "Fisherman" },
  { value: "coast_guard", label: "Coast Guard" },
  { value: "researcher", label: "Researcher" },
  { value: "maritime_operator", label: "Maritime Operator" },
  { value: "coastal_authority", label: "Coastal Authority" },
  { value: "other", label: "Other" },
] as const;

// ---------------------------------------------------------------------------
// Schemas
// ---------------------------------------------------------------------------

const loginSchema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
});

const registerSchema = z
  .object({
    name: z.string().min(1, "Name is required.").max(255),
    email: z.string().email("Enter a valid email address."),
    password: z.string().min(8, "Password must be at least 8 characters."),
    confirm_password: z.string().min(8, "Please confirm your password."),
    user_type: z.string().min(1, "Select your role."),
  })
  .refine((d) => d.password === d.confirm_password, {
    message: "Passwords do not match.",
    path: ["confirm_password"],
  });

type LoginFormValues = z.infer<typeof loginSchema>;
type RegisterFormValues = z.infer<typeof registerSchema>;

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PasswordInput({
  field,
  placeholder,
}: {
  field: React.InputHTMLAttributes<HTMLInputElement> & { value?: string };
  placeholder?: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <Input
        {...field}
        type={show ? "text" : "password"}
        placeholder={placeholder ?? "Password"}
        className="pr-10"
      />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
        aria-label={show ? "Hide password" : "Show password"}
      >
        {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Login form
// ---------------------------------------------------------------------------

function LoginTab({ onSuccess }: { onSuccess: () => void }) {
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = async (values: LoginFormValues) => {
    setLoading(true);
    setError(null);
    try {
      await login(values);
      onSuccess();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                  <Input
                    {...field}
                    id="login-email"
                    type="email"
                    placeholder="captain@example.com"
                    className="pl-9"
                    autoComplete="email"
                  />
                </div>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <PasswordInput field={field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {error && (
          <p className="text-sm text-danger rounded-md border border-danger/30 bg-danger/10 px-3 py-2">
            {error}
          </p>
        )}

        <Button type="submit" id="login-submit" className="w-full" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </Form>
  );
}

// ---------------------------------------------------------------------------
// Register form
// ---------------------------------------------------------------------------

function RegisterTab({ onSuccess }: { onSuccess: () => void }) {
  const { register } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const form = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      name: "",
      email: "",
      password: "",
      confirm_password: "",
      user_type: "other",
    },
  });

  const onSubmit = async (values: RegisterFormValues) => {
    setLoading(true);
    setError(null);
    try {
      await register({ ...values, preferred_language: "en" });
      onSuccess();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        {/* Name */}
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                  <Input
                    {...field}
                    id="register-name"
                    placeholder="Captain Daras"
                    className="pl-9"
                    autoComplete="name"
                  />
                </div>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Email */}
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                  <Input
                    {...field}
                    id="register-email"
                    type="email"
                    placeholder="captain@example.com"
                    className="pl-9"
                    autoComplete="email"
                  />
                </div>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* User Type */}
        <FormField
          control={form.control}
          name="user_type"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Role</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger id="register-user-type" className="w-full">
                    <Users className="mr-2 size-4 text-muted-foreground" />
                    <SelectValue placeholder="Select your role" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {USER_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Password */}
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <PasswordInput field={field} placeholder="Min. 8 characters" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Confirm Password */}
        <FormField
          control={form.control}
          name="confirm_password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Confirm Password</FormLabel>
              <FormControl>
                <PasswordInput field={field} placeholder="Repeat password" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {error && (
          <p className="text-sm text-danger rounded-md border border-danger/30 bg-danger/10 px-3 py-2">
            {error}
          </p>
        )}

        <Button type="submit" id="register-submit" className="w-full" disabled={loading}>
          {loading ? "Creating account…" : "Create account"}
        </Button>
      </form>
    </Form>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface AuthModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AuthModal({ open, onOpenChange }: AuthModalProps) {
  const handleSuccess = () => onOpenChange(false);
  const handleGuest = () => onOpenChange(false);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        id="auth-modal"
        className="max-w-md gap-0 overflow-hidden p-0 z-[1000]"
        style={{
          background: "linear-gradient(145deg, var(--deep) 0%, var(--abyss) 100%)",
          border: "1px solid var(--border)",
        }}
      >
        {/* Header */}
        <DialogHeader className="border-b border-border px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/20">
              <Fish className="size-5 text-primary" />
            </div>
            <div>
              <DialogTitle className="text-base font-semibold text-shell">
                Welcome to ORCA
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                Sign in for a personalised experience, or continue as a guest.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* Tabs */}
        <div className="px-6 py-5">
          <Tabs defaultValue="login">
            <TabsList className="mb-5 grid w-full grid-cols-2">
              <TabsTrigger value="login" id="auth-tab-login">
                Sign in
              </TabsTrigger>
              <TabsTrigger value="register" id="auth-tab-register">
                Register
              </TabsTrigger>
            </TabsList>

            <TabsContent value="login" className="mt-0">
              <LoginTab onSuccess={handleSuccess} />
            </TabsContent>

            <TabsContent value="register" className="mt-0">
              <RegisterTab onSuccess={handleSuccess} />
            </TabsContent>
          </Tabs>

          {/* Guest divider */}
          <div className="mt-5 flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted-foreground">or</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          <Button
            id="continue-as-guest"
            variant="ghost"
            className="mt-3 w-full text-muted-foreground hover:text-foreground"
            onClick={handleGuest}
          >
            <Lock className="mr-2 size-4" />
            Continue as Guest
          </Button>

          <p className="mt-3 text-center text-[11px] text-muted-foreground">
            Guest mode gives full access to all ORCA features without an account.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
