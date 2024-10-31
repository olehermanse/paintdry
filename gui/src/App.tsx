import ResourcesView from "./ResourcesView";
import SingleResourceView from "./SingleResourceView";
import TableView from "./TableView";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./Layout";
import ConfigView from "./ConfigView";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/ui" element={<Layout />}>
          <Route index element={<ResourcesView />} />
          <Route path="/ui/resources" element={<ResourcesView />} />
          <Route path="/ui/resources/:id" element={<SingleResourceView />} />
          <Route
            path="/ui/observations"
            element={
              <TableView
                api={"/api/observations"}
                header={"Observations"}
                fields={[
                  "id",
                  "resource",
                  "module",
                  "attribute",
                  "value",
                  "first_seen",
                  "last_changed",
                  "last_seen",
                ]}
              />
            }
          />
          <Route path="/ui/config" element={<ConfigView />} />
          <Route path="*" element={<div> Other option </div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
