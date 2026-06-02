import { createContext, useContext } from 'react';
import type { DockviewApi } from 'dockview-react';

export const DockviewApiContext = createContext<DockviewApi | null>(null);
export const useDockviewApi = () => useContext(DockviewApiContext);
