import React from 'react';
// Layout
import RootLayout from '@/app/layout';
// FilePond for Uploads
import { FilePond, registerPlugin } from 'react-filepond';
import 'filepond/dist/filepond.min.css';
// For FilePond previews: Images
import 'filepond-plugin-image-preview/dist/filepond-plugin-image-preview.css';
import FilePondPluginImagePreview from 'filepond-plugin-image-preview';
// For FilePond previews: PDFs
import FilePondPluginFileValidateType from 'filepond-plugin-file-validate-type';
//For Progress Bar on upload
import ProgressBarPopup from '@/components/ProgresssBarPopup';
import axios from 'axios';


registerPlugin(FilePondPluginImagePreview);
registerPlugin(FilePondPluginFileValidateType);

// Code for the rendering of elements
function FileUploader() {
  // The fields the user should be able to edit by himself
  const metadataFields = ["Dokumententitel", "Herausgeber", "Verlag", "Erscheinungsort", "Erscheinungsdatum", "Erscheinungsjahr", "Erlassdatum", "Inkrafttreten", "Seitenzahl"]
  const [metadataFieldValues, setMetadataFieldValues] = React.useState(metadataFields.map(() => ''))
  // The uploaded files
  const [files, setFiles] = React.useState([]);
  // For task progress bar
  const [showPopup, setShowPopup] = React.useState(false);
  const [taskId, setTaskId] = React.useState(0); // Set your parameter value here
  // filePond Reference
  const filePondRef = React.useRef(null)

  // Helper function for posting the request to the backend server
  const postRegulationFiles = async () => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('regulation_files', file);
    });

    //const metadataObject = {}
    for (var i = 0; i < metadataFields.length; i++) {
      formData.append(metadataFields[i].toLowerCase(), metadataFieldValues[i])
    }
    //metadataObject["type"] = 'application/json'
    //formData.append('regulation_metadata', metadataObject)  // JSON.stringify(metadataObject)

    try {
      const response = await axios.post('http://192.168.37.129:8000/create/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data', // TODO Vielleicht nicht nötig?
        }
      });
      setTaskId(response.data.task_id)
      // TODO Clear input after post request
      setFiles([])
      if (filePondRef.current) {
        filePondRef.current.getFiles().forEach(file => {
          filePondRef.current.removeFile(file);
        });
      }
      setMetadataFieldValues(metadataFields.map(() => ''))
      openPopup();
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const openPopup = () => {
    setShowPopup(true);
  };

  const closePopup = () => {
    setShowPopup(false);
  };

  // Helper function for updating the values that are stored in the text input fields
  const updateMetadataFieldValue = (index, value) => {
    const updatedValues = [...metadataFieldValues]
    updatedValues[index] = value
    setMetadataFieldValues(updatedValues)
  }

  // TODO Alles, was kein FilePond ist, in der post request adden
  return (
    <div>
      {metadataFields.map((value, index) => (
        <div key={index}>
          <label htmlFor={`${value}Input`}>{value}:</label>
          <input type="text"
            id={`${value}Input`}
            value={metadataFieldValues[index]}
            className='form-control'
            placeholder={`${value} eingeben (Optional)`}
            onChange={(e) => updateMetadataFieldValue(index, e.target.value)}></input>
        </div>
      ))}
      <div>
        <FilePond
          ref={filePondRef}
          allowMultiple={true}
          acceptedFileTypes={['image/*', 'application/pdf']}
          type="file"
          onupdatefiles={(fileItems) => {
            setFiles(fileItems.map(fileItem => fileItem.file))
            console.log(fileItems);
          }}>
        </FilePond>
        <button type="button" className="btn btn-primary" onClick={postRegulationFiles}>Dateien hochladen</button>
        <div>
          <ProgressBarPopup show={showPopup} onClose={closePopup} taskId={taskId} />
        </div>
      </div>
    </div>
  )
}

function Upload() {
  return (
    <RootLayout>
      <div>
        <h1>Neue Verordnungen hochladen</h1>
        <p>Hier können neue Verordnungen hochgeladen werden</p>
        <FileUploader />
      </div>
    </RootLayout>
  );
}

export default Upload;