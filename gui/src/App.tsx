import './App.css'
import ResourcesView from './ResourcesView';
import {
  BrowserRouter,
  Routes,
  Route
} from "react-router-dom";
import Layout from './Layout';

function App() {
  return (
  <BrowserRouter>

    <Routes>
      <Route path="/ui" element={<Layout />}>
        <Route index element={<ResourcesView />} />
        <Route path="/ui/resources" element={<ResourcesView />} />
        <Route path="/ui/other" element={<div> Other option </div>} />
        <Route path="/ui/other/:id" element={<div> Other option </div>} />
        <Route path="*" element={<div> Other option </div>} />
      </Route>
    </Routes>
  </BrowserRouter>

  );
}

export default App
