import * as React from 'react';
import { Box, Tab, Tabs } from "@mui/material";
import { Outlet, useLocation, useNavigate, useParams } from "react-router-dom";

function a11yProps(index: number) {
  return {
    id: `simple-tab-${index}`,
    'aria-controls': `simple-tabpanel-${index}`,
  };
}

const Layout = () => {
  const navigate = useNavigate();
  const loc = useLocation();
  const { id } = useParams();
  const index = loc.pathname.includes("resources") ? 0 : 1;
  const [value, setValue] = React.useState(index);
  const handleChange = (event: React.SyntheticEvent, newValue: number) => {
    console.log(event);
      setValue(newValue);
      navigate(newValue === 0 ? "resources" : "other");
    };
  return (
    <>
      {id}
      <Box sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={value} onChange={handleChange} aria-label="basic tabs example">
            <Tab label="Resources" {...a11yProps(0)} />
            <Tab label="Other" {...a11yProps(1)} />
          </Tabs>
        </Box>
      </Box>
      <Outlet />
    </>
  )
};

export default Layout;
