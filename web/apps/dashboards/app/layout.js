// web/apps/dashboards/app/layout.js
import './globals.css';
import Nav from '../components/Nav';

export const metadata = {
  title: 'Portfolio Analytics',
  description: 'Investment analytics dashboards',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <div className="container">{children}</div>
      </body>
    </html>
  );
}
