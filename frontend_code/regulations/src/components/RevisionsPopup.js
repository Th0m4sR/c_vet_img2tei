import React, { useState } from 'react';
import { Modal, Button } from 'react-bootstrap';

function RevisionPopup({ data, showModal, onClose, onItemClick }) {
  console.log("Popup Data")
  console.log(data)

  return (
    <Modal show={showModal} onHide={onClose}>
      <Modal.Header closeButton>
        <Modal.Title>Letzte Änderungen</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <ul>
          <Button variant="dark" onClick={() => onItemClick(0)}>Ursprüngliches Dokument laden</Button>
          {data.map((item, index) => (
            <li key={index}>
              {Object.keys(item).map((key, subIndex) => (
                <div key={subIndex}>
                  <strong>{key}:</strong> {item[key]}
                </div>
              ))}
              <Button onClick={() => onItemClick(item.version)}>Version laden</Button>
            </li>
          ))}
        </ul>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onClose}>
          Schließen
        </Button>
      </Modal.Footer>
    </Modal>
  );
}

export default RevisionPopup;
