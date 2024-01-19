import Link from 'next/link'
import { Navbar, Container, Nav } from 'react-bootstrap';



function NavBar() {
    return (
      <Navbar bg="light" expand="lg">
        <Container>
          <Navbar.Brand href="/">Startseite</Navbar.Brand>
          <Navbar.Toggle aria-controls="navbar-nav" />
          <Navbar.Collapse id="navbar-nav">
            <Nav className="me-auto">
              <Nav.Link href="/search">Suche</Nav.Link>
              <Nav.Link href="/upload">Upload</Nav.Link>
            </Nav>
          </Navbar.Collapse>
        </Container>
      </Navbar>
    );
  }

export default NavBar