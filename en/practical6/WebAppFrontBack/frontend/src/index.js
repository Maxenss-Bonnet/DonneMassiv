import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';

// Point d'entrée de l'application React
const App = () => {
  const [message, setMessage] = useState('Loading...');
  const [error, setError] = useState(null);

// Utilisation de useEffect pour effectuer une requête fetch au démarrage du composant
  useEffect(() => {
    fetch('http://localhost:5000/message')  
      .then(res => res.json()) // Convertit la réponse en JSON
      .then(data => setMessage(data.text)) // Met à jour le message avec la réponse
      .catch(err => { // Gère les erreurs de la requête
        console.error('Error fetching message:', err);
        setError('Failed to fetch message');
      });
  }, []);

  return ( // Rendu du composant
    <div>
      <h1>Message from Backend:</h1>
      {error ? <p>{error}</p> : <p>{message}</p>}
    </div>
  );
};

// Création de la racine de l'application React
const root = ReactDOM.createRoot(document.getElementById('message'));
root.render(<App />);
