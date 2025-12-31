/**
 * ProjectHeader - Displays project name, address, and status badge
 */

import { CheckCircle } from 'lucide-react';

interface ProjectHeaderProps {
  buildingName: string;
  buildingAddress: string;
  isComplete?: boolean;
}

export default function ProjectHeader({
  buildingName,
  buildingAddress,
  isComplete = true,
}: ProjectHeaderProps) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <h2 className="font-bold text-gray-800 text-lg">{buildingName || 'Projekt'}</h2>
        <p className="text-sm text-gray-500">{buildingAddress || 'Adresse'}</p>
      </div>
      {isComplete && (
        <span className="bg-green-100 text-green-700 text-xs px-2.5 py-1 rounded-full font-medium flex items-center gap-1">
          <CheckCircle className="w-3 h-3" />
          Vollständig
        </span>
      )}
    </div>
  );
}
