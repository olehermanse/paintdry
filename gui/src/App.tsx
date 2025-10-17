import TableView from "./TableView";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./Layout";
import ConfigView from "./ConfigView";
import SingleJsonView from "./SingleJsonView";
import SearchView from "./SearchView";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/ui" element={<Layout />}>
          <Route
            index
            element={
              <TableView
                api={"/api/resources"}
                header={"Resources"}
                fields={[
                  "id",
                  "resource",
                  "module",
                  "source",
                  "first_seen",
                  "last_seen",
                ]}
              />
            }
          />
          <Route
            path="/ui/resources"
            element={
              <TableView
                api={"/api/resources"}
                header={"Resources"}
                fields={[
                  "id",
                  "resource",
                  "module",
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
          <Route
            path="/ui/changes"
            element={
              <TableView
                api={"/api/changes"}
                header={"Changes"}
                fields={[
                  "id",
                  "resource",
                  "module",
                  "attribute",
                  "old_value",
                  "new_value",
                  "timestamp",
                ]}
              />
            }
          />
          <Route
            path="/ui/changes/:id"
            element={<SingleJsonView api={"/api/changes"} />}
          />
          <Route
            path="/ui/history"
            element={
              <TableView
                api={"/api/history"}
                header={"History"}
                fields={[
                  "id",
                  "resource",
                  "module",
                  "attribute",
                  "value",
                  "timestamp",
                ]}
              />
            }
          />
          <Route
            path="/ui/history/:id"
            element={<SingleJsonView api={"/api/history"} />}
          />
          <Route path="/ui/config" element={<ConfigView />} />
          <Route path="/ui/search" element={<SearchView />} />
          <Route path="*" element={<div> Page not found... </div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
