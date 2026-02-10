import { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
	const [user, setUser] = useState(() => {
		try {
			const saved = sessionStorage.getItem('auth_user');
			return saved ? JSON.parse(saved) : null;
		} catch { return null; }
	});

	useEffect(() => {
		if (user) sessionStorage.setItem('auth_user', JSON.stringify(user));
		else sessionStorage.removeItem('auth_user');
	}, [user]);

	const login = (username, password) => {
		if (username === 'admin' && password === 'admin') {
			const u = { username: 'admin', name: 'SRE Admin', role: 'admin', email: 'admin@resilience.io' };
			setUser(u);
			return true;
		}
		return false;
	};

	const logout = () => setUser(null);

	return (
		<AuthContext.Provider value={{ user, login, logout, isAuthenticated: !!user }}>
			{children}
		</AuthContext.Provider>
	);
}

export const useAuth = () => useContext(AuthContext);
