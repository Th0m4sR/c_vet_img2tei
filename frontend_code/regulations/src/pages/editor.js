import React, { useEffect, version } from 'react';
import { useRouter } from 'next/router';
// Layout
import RootLayout from '@/app/layout';
// Image Viewer Dependencies
import Gallery from 'react-image-gallery';
import 'react-image-gallery/styles/css/image-gallery.css';
// XML Editor Dependencies
import AceEditor from 'react-ace'
import "ace-builds/src-noconflict/mode-xml";
import "ace-builds/src-noconflict/theme-monokai";
import "ace-builds/src-noconflict/ext-language_tools";
import axios from 'axios';
import Alert from 'react-bootstrap/Alert';
import RevisionPopup from '@/components/RevisionsPopup'

/*const images = [
    { thumbnail: '/imgs/brd_fachkraft_kueche_2022/brd_fachkraft_kueche_2022-1.png', original: '/imgs/brd_fachkraft_kueche_2022/brd_fachkraft_kueche_2022-1.png', description: 'Page 1' },
    { thumbnail: '/imgs/brd_fachkraft_kueche_2022/brd_fachkraft_kueche_2022-2.png', original: '/imgs/brd_fachkraft_kueche_2022/brd_fachkraft_kueche_2022-2.png', description: 'Page 2' },
    { thumbnail: '/imgs/brd_fachkraft_kueche_2022/brd_fachkraft_kueche_2022-3.png', original: '/imgs/brd_fachkraft_kueche_2022/brd_fachkraft_kueche_2022-3.png', description: 'Page 3' },
];*/

// This is for representing the elements on the page

function ImageViewer() {
    const router = useRouter();
    const { page_images, regulation, title, time, revisions } = router.query;
    const images = [];
    page_images.forEach((img) => {
        images.push({ thumbnail: img, original: img, description: "description" })
    })
    console.log(images)
    return (
        <div>
            <Gallery items={images} />
        </div>
    );
}


function XMLeditor() {
    const router = useRouter();
    const { regulation, title, time, exist_name, revisions } = router.query;

    const [regulationText, setRegulationText] = React.useState(regulation)

    const [showAlert, setShowAlert] = React.useState(false)
    const [alertMessage, setAlertMessage] = React.useState('')
    const [alertVariant, setAlertVariant] = React.useState('info')

    console.log("REVISIONS")
    console.log(revisions)

    const [revisionObjects, setRevisionObjects] = React.useState(JSON.parse(revisions).map((rev) => JSON.parse(rev)))
    const [showRevisionModal, setShowRevisionModal] = React.useState(false)

    const submitChanges = async () => {
        const updatedRegulation = {
            exist_name: exist_name,
            xml_regulation: regulationText,
        }
        const response = await axios.post(`http://192.168.37.129:8000/update/`, updatedRegulation)
        setShowAlert(true)

        setAlertMessage(response.data.message)
        if(response.data.success){
            setAlertVariant("success")
            // setRevision(null)
        } else {
            setAlertVariant("danger")
        }
    }

    const onChange = (newValue) => {
        setRegulationText(newValue)
    }

    const dismissAlert = () => {
        setShowAlert(false)
    }

    const showModal = () => {setShowRevisionModal(true)}
    const closeModal = () => {setShowRevisionModal(false)}

    console.log("ROUTER PARAMS")
    console.log(router.query)

    const setRevision = async (version) => {
        console.log(version)
        const response = await axios.get(`http://192.168.37.129:8000/regulations/${exist_name}?version=${version}`)
        console.log(response.data)
        setRegulationText(response.data.regulation)
        setRevisionObjects(response.data.revisions)
        setShowRevisionModal(false)
    }

    const deleteRegulation = async () => {
        const response = await axios.delete(`http://192.168.37.129:8000/delete/${exist_name}`)
        console.log(response.data)
        if(response.data.success){
            setAlertVariant("success")
            setAlertMessage(response.data.message)
            setShowAlert(true)
            router.push('/');
        } else {
            setAlertVariant("danger")
            setAlertMessage(response.data.message)
            setShowAlert(true)
        }
    }

    return (
        <div>
            <AceEditor
                mode="xml"
                value={regulationText}
                theme="monokai"
                onChange={onChange}
                name="xmleditor"
                highlightActiveLine={true}
                showGutter={true}
                showPrintMargin={true}
                showLineNumbers={true}
                editorProps={{ $blockScrolling: true }}
                width='750px'
                height='800px'
            ></AceEditor>
            <button type="button" className="btn btn-success" onClick={submitChanges}>Änderungen Speichern</button>
            <Alert show={showAlert} variant={alertVariant} dismissible="true" onClose={dismissAlert}>
                <p>{alertMessage}</p>
            </Alert>
            <button type="button" className="btn btn-info" onClick={showModal}>Versionen anzeigen</button>
            <RevisionPopup  data={revisionObjects} showModal={showRevisionModal} onClose={closeModal} onItemClick={setRevision}/>
            <button type="button" className="btn btn-danger" onClick={deleteRegulation}>Verordnung löschen</button>
        </div>
    )
}

function Editor() {
    // Maybe I will use Ace Editor for the start...
    return (
        <RootLayout>
            <div>
                <div className='text-center'>
                    <h1>Editor</h1>
                </div>
                <div className="container" style={{ display: 'flex' }}>
                    <div className="column image-column" style={{ flex: 1 }}>
                        <div className="content" style={{ width: 500 + 'px', height: 800 + 'px' }}>
                            <ImageViewer />
                        </div>
                    </div>
                    <div className="column editor-column" style={{ flex: 1 }}>
                        <div className="scrollable-container" style={{ width: 1000 + 'px', height: 1000 + 'px', overflow: 'auto' }}>
                            <div className="content">
                                <XMLeditor />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </RootLayout>
    )
}

export default Editor;