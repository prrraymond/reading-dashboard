import React from 'react';

// export const Card = ({ children, className }: { children: React.ReactNode; className?: string }) => {
//   return (
//     <div className={`rounded-lg bg-white shadow p-4 ${className || ''}`}>
//       {children}
//     </div>
//   );
// };

// export const CardContent = ({ children, className }: { children: React.ReactNode; className?: string }) => (
//   <div className={`${className || ''}`}>{children}</div>
// );

// export const CardHeader = ({ children, className }: { children: React.ReactNode; className?: string }) => (
//   <div className={`border-b p-4 ${className || ''}`}>{children}</div>
// );

// export const CardTitle = ({ children, className }: { children: React.ReactNode; className?: string }) => (
//   <h2 className={`text-xl font-bold text-gray-800 ${className || ''}`}>{children}</h2>
// );
// export const Card = ({ children, className }: { children: React.ReactNode; className?: string }) => {
//   return (
//     <div className={`rounded-lg bg-white shadow p-4 ${className || ''}`}>
//       {children}
//     </div>
//   );
// };
export const Card = ({ children, className }: { children: React.ReactNode; className?: string }) => {
  return (
    <div className={`rounded-lg shadow p-4 ${className || ''}`}>
      {children}
    </div>
  );
};

export const CardContent = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <div className={`p-4 ${className || ''}`}>{children}</div>
);

export const CardHeader = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <div className={`border-b p-4 ${className || ''}`}>{children}</div>
);

export const CardTitle = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <h2 className={`text-xl font-bold text-gray-800 ${className || ''}`}>{children}</h2>
);
