import React, { useState, useEffect } from 'react';
import { Button, Modal, ProgressBar } from 'react-bootstrap';
import axios from 'axios';
import Link from 'next/link'

const ProgressBarPopup = ({ show, onClose, taskId }) => {
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [showAbortButton, setShowAbortButton] = useState(true)
  const [createdResource, setCreatedResource] = useState(null)

  const abortUpload = async () => {
    try {
      const response = await axios.get(`http://192.168.37.129:8000/cancel_task/${taskId}`);
      const newProgress = response.data.progress;
      const newMessage = response.data.content.message;
      setProgress(newProgress);
      setMessage(newMessage);
      setShowAbortButton(false)
    } catch (error) {
      console.error("Error fetching progress:", error);
    }
  }

  useEffect(() => {
    let pollInterval;

    // Start polling when show is true
    if (show && progress != 100) {
      pollInterval = setInterval(async () => {
        try {
          const response = await axios.get(`http://192.168.37.129:8000/task_progress/${taskId}`);
          const newProgress = response.data.progress;
          const newMessage = response.data.content.message;
          if (newProgress >= 100) {
            setShowAbortButton(false)
          }
          setProgress(newProgress);
          setMessage(newMessage);
          if ('resource' in response.data.content) {
            setCreatedResource(response.data.content.resource)
            console.log(createdResource)
          }
        } catch (error) {
          console.error("Error fetching progress:", error);
        }
      }, 1000); // Polling interval in milliseconds
    }

    // Cleanup the interval when show is false or the component unmounts
    return () => {
      clearInterval(pollInterval);
    };
  }, [show, taskId]);

  return (
    <Modal show={show} onHide={onClose}>
      <Modal.Header closeButton>
        <Modal.Title>Upload-Fortschritt</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <ProgressBar now={progress} label={`${progress}%`} />
        <div style={{ marginTop: '10px' }}>{message}</div>
      </Modal.Body>
      {showAbortButton ?
        <Button variant="danger" onClick={abortUpload}>
          Vorgang abbrechen
        </Button> : ''
      }
      {createdResource != null ?
        <Button variant="success">
          <Link href={{
            pathname: "/editor",
            query: {
              "regulation": createdResource.regulation,
              "title": createdResource.title,
              "time": createdResource.time,
              "page_images": createdResource.page_images,
              "exist_name": createdResource.exist_name,
              "revisions": JSON.stringify(createdResource.revisions.map((r) => JSON.stringify(r)))
            },
          }}>
            Verordnung anschauen
          </Link>
        </Button> : ''}
    </Modal>
  );
};

export default ProgressBarPopup;
