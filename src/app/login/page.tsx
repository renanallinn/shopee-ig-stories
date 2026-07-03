import LoginForm from "./LoginForm";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
      <div className="text-center">
        <h1 className="text-xl font-semibold">Shopee Stories</h1>
        <p className="text-sm text-black/60 dark:text-white/60">
          Entre para conectar sua loja Shopee e seu Instagram.
        </p>
      </div>
      <LoginForm />
    </main>
  );
}
