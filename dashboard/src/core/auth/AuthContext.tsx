import React, { createContext, useContext, useState, useEffect } from 'react';
import { OfficerUser, UserRole } from './authTypes';

interface AuthContextType {
  user: OfficerUser | null;
  isAuthenticated: boolean;
  login: (email: string, role?: UserRole) => Promise<void>;
  logout: () => void;
  switchRole: (role: UserRole) => void;
  availableOfficers: OfficerUser[];
}

export const DEMO_OFFICERS: OfficerUser[] = [
  {
    id: 'off-001',
    name: 'Priya Sharma',
    email: 'priya.sharma@civicsense.gov.in',
    badgeNumber: 'CS-TRG-042',
    department: 'Roads & Bridges',
    role: 'TRIAGE_OFFICER',
  },
  {
    id: 'off-002',
    name: 'Rajesh Kumar',
    email: 'rajesh.kumar@civicsense.gov.in',
    badgeNumber: 'CS-MGR-018',
    department: 'Solid Waste Management',
    role: 'DEPARTMENT_MANAGER',
  },
  {
    id: 'off-003',
    name: 'Ananya Verma',
    email: 'ananya.verma@civicsense.gov.in',
    badgeNumber: 'CS-INS-089',
    department: 'Water Supply & Sewerage',
    role: 'FIELD_INSPECTOR',
  },
  {
    id: 'off-004',
    name: 'Devraj Menon',
    email: 'devraj.menon@civicsense.gov.in',
    badgeNumber: 'CS-ADM-001',
    department: 'Town Planning & Enforcement',
    role: 'SUPER_ADMIN',
  },
];

const AUTH_STORAGE_KEY = 'civicsense_active_officer';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<OfficerUser | null>(() => {
    const saved = localStorage.getItem(AUTH_STORAGE_KEY);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        // Fall back to default
      }
    }
    return DEMO_OFFICERS[0];
  });

  useEffect(() => {
    if (user) {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    }
  }, [user]);

  const login = async (email: string, role?: UserRole) => {
    const matched = DEMO_OFFICERS.find(
      (o) => o.email.toLowerCase() === email.toLowerCase() || (role && o.role === role)
    );
    if (matched) {
      setUser(matched);
    } else {
      // Create guest session
      setUser({
        id: 'off-guest',
        name: email.split('@')[0],
        email,
        badgeNumber: 'CS-DEMO-999',
        department: 'General Public Works',
        role: role || 'TRIAGE_OFFICER',
      });
    }
  };

  const logout = () => {
    setUser(null);
  };

  const switchRole = (role: UserRole) => {
    const officer = DEMO_OFFICERS.find((o) => o.role === role);
    if (officer) {
      setUser(officer);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        login,
        logout,
        switchRole,
        availableOfficers: DEMO_OFFICERS,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
