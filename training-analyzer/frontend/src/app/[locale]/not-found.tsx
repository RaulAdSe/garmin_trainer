import { Link } from '@/i18n/navigation';

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <h1 className="text-6xl font-bold text-teal-400 mb-4">404</h1>
      <h2 className="text-2xl font-semibold text-gray-200 mb-4">
        Page Not Found
      </h2>
      <p className="text-gray-400 mb-8 max-w-md">
        The page you are looking for does not exist or has been moved.
      </p>
      <Link
        href="/"
        className="px-6 py-3 bg-teal-600 hover:bg-teal-700 text-white rounded-lg transition-colors"
      >
        Return Home
      </Link>
    </div>
  );
}
