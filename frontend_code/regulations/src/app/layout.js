// import './globals.css'
import { Inter } from 'next/font/google'
// Das hier ist jetzt neu von mir
import 'bootstrap/dist/css/bootstrap.min.css'
import NavBar from '@/components/NavBar'

const inter = Inter({ subsets: ['latin'] })

export default function RootLayout({ children }) {
  return (
    <div>
        <NavBar></NavBar>
        <div>{children}</div>
    </div>
  )
}
