import { Link } from 'react-router-dom';

export default function NotFound() {
	return (
		<div className="flex h-[70vh] flex-col items-center justify-center">
			<p className="text-6xl font-semibold text-zinc-200">404</p>
			<p className="mt-2 text-sm text-zinc-500">Page not found</p>
			<Link to="/" className="mt-4 text-sm text-blue-600 hover:underline">
				Back to overview
			</Link>
		</div>
	);
}
