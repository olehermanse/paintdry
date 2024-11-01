import TableView from "./TableView";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./Layout";
import ConfigView from "./ConfigView";
import SingleJsonView from "./SingleJsonView";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/ui" element={<Layout />}>
          <Route index element={<ConfigView />} />
          <Route
            path="/ui/resources"
            element={
              <TableView
                api={"/api/resources"}
                header={"Resources"}
                fields={[
                  "id",
                  "resource",
                  "modules",
                  "source",
                  "first_seen",
                  "last_seen",
                ]}
              />
            }
          />
          <Route
            path="/ui/resources/:id"
            element={<SingleJsonView api={"/api/resources"} />}
          />
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
          <Route
            path="/ui/observations/:id"
            element={<SingleJsonView api={"/api/observations"} />}
          />
          <Route path="/ui/config" element={<ConfigView />} />
          <Route path="*" element={<div> Page not found... </div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
