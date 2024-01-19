import React from 'react';
import Link from 'next/link';
import axios from 'axios'
// Layout
import RootLayout from '@/app/layout';
import { data, error } from 'jquery';

function SearchInputFields() {
  // TODO Fulltext
  const searchFields = ["Text", "Dokumententitel", "Herausgeber", "Verlag", "Erscheinungsort", "Erscheinungsdatum", "Erscheinungsjahr", "Erlassdatum", "Inkrafttreten", "Seitenzahl"]
  const [searchFieldValues, setSearchFieldValues] = React.useState(searchFields.map(() => ''))
  const [searchResults, setSearchResults] = React.useState([])

  // Helper function for posting the request to the backend server
  const queryRegulations = async () => {
    const queryParams = {}
    for (var i = 0; i < searchFields.length; i++) {
      queryParams[`${searchFields[i].toLowerCase()}`] = searchFieldValues[i]
    }
    const jsonQueryParams = JSON.stringify(queryParams)
    const options = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json', // TODO Vielleicht nicht nötig?
      },
      body: jsonQueryParams
    }

    axios.post('http://192.168.37.129:8000/search/', queryParams, { headers: { 'Ccontent-Type': 'application/json' } })
      .then(response => {
        //console.log(response)
        const data = response.data
        setSearchResults(data)
      })
      .catch(error => {
        console.log(error)
      })
  };

  // Helper function for updating the values that are stored in the text input fields
  const updateSearchFieldValue = (index, value) => {
    const updatedValues = [...searchFieldValues]
    updatedValues[index] = value
    setSearchFieldValues(updatedValues)
  }
  // TODO Löschen
  searchResults.forEach((r) => {
    console.log(r)
  })
  return (
    <div>
      {searchFields.map((value, index) => (
        <div key={index}>
          <label htmlFor={`${value}Input`}>{value}:</label>
          <input type="text"
            id={`${value}Input`}
            value={searchFieldValues[index]}
            className='form-control'
            placeholder={`${value} eingeben (Optional)`}
            onChange={(e) => updateSearchFieldValue(index, e.target.value)}></input>
        </div>
      ))}
      <button type="button" className="btn btn-primary" onClick={queryRegulations}>Suchen</button>
      <ul className='list-group'>
        {searchResults.map((result, index) => (
          <li key={index} className='list-group-item'>
            <Link href={{
              pathname: "/editor",
              query: {
                "regulation": result.regulation,
                "title": result.title,
                "time": result.time,
                "page_images": result.page_images,
                "exist_name": result.exist_name,
                "revisions": JSON.stringify(result.revisions.map((r) => JSON.stringify(r)))
            },
            }}>{result.title} - {result.time}</Link>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function Home() {
  return (
    <RootLayout>
      <div>
        <h1>Suche nach Dokumenten</h1>
        <p>Hier kann nach Dokumenten gesucht werden. Mindestens eins der Felder muss angegeben werden</p>
        <SearchInputFields />
      </div>
    </RootLayout>
  );
}
