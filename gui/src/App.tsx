import ResourcesView from './ResourcesView';
import SingleResourceView from './SingleResourceView';
import ObservationsView from './ObservationsView';
import {
  BrowserRouter,
  Routes,
  Route,
} from "react-router-dom";
import Layout from './Layout';
import ConfigView from './ConfigView';

function App() {
  return (
  <BrowserRouter>
    <Routes>
      <Route path="/ui" element={<Layout />}>
        <Route index element={<ResourcesView />} />
        <Route path="/ui/resources" element={<ResourcesView />} />
        <Route path="/ui/resources/:id" element={<SingleResourceView />} />
        <Route path="/ui/observations" element={<ObservationsView />} />
        <Route path="/ui/config" element={<ConfigView />} />
        <Route path="*" element={<div> Other option </div>} />
      </Route>
    </Routes>
  </BrowserRouter>
  );
}

export default App
