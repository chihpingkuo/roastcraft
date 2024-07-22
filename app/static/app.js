async function App() {
  const width = 800;
  const height = 500;
  const marginTop = 20;
  const marginRight = 20;
  const marginBottom = 30;
  const marginLeft = 40;

  let store = Alpine.reactive({
    channels: settings.channels.map((c) => ({
      id: c.id,
      color: c.color,
      data: [],
      ror: [],
      ror_filtered: [],
      ror_smoothed: []
    })),
  });

  // Declare the x (horizontal position) scale.
  const xScale = d3
    .scaleLinear()
    .domain([0, 900])
    .range([marginLeft, width - marginRight]);

  // Declare the y (vertical position) scale.
  const yScale = d3
    .scaleLinear()
    .domain([0, 400])
    .range([height - marginBottom, marginTop]);

  // Declare the y (vertical position) scale.
  const yScaleROR = d3
  .scaleLinear()
  .domain([0, 30])
  .range([height - marginBottom, marginTop]);


  // Declare the line generator.
  const line = d3.line()
    .x((p) => xScale(p.t))
    .y((p) => yScale(p.v));

  const lineROR = d3.line()
    .x((p) => xScale(p.t))
    .y((p) => yScaleROR(p.v));


  // Create the SVG container.
  const svg = d3.create("svg").attr("width", width).attr("height", height);

  // Add the x-axis.
  svg
    .append("g")
    .attr("transform", `translate(0,${height - marginBottom})`)
    .call(d3.axisBottom(xScale));

  // Add the y-axis.
  svg
    .append("g")
    .attr("transform", `translate(${marginLeft},0)`)
    .call(d3.axisLeft(yScale));

  svg
    .append("g")
    .attr("transform", `translate(${width - marginRight},0)`)
    .call(d3.axisRight(yScaleROR));


  store.channels.forEach((channel) => {
    svg
      .append("path")
      .attr("id", channel.id)
      .attr("fill", "none")
      .attr("stroke", channel.color)
      .attr("stroke-width", 1.5)
      .attr("d", line(channel.data));
  });

  svg
  .append("path")
  .attr("id", "BT_ROR")
  .attr("fill", "none")
  .attr("stroke", "#2E8B57")
  .attr("stroke-width", 1)
  .attr("d", lineROR(store.channels[0].ror));

  svg
  .append("path")
  .attr("id", "BT_ROR_SMOOTH")
  .attr("fill", "none")
  .attr("stroke", "#0000FF")
  .attr("stroke-width", 2)
  .attr("d", lineROR(store.channels[0].ror_smoothed));


  Alpine.effect(() => {
    store.channels.forEach((channel) => {
      d3.select("#" + channel.id).attr("d", line(channel.data));
    });
    d3.select("#" + "BT_ROR").attr("d", lineROR(store.channels[0].ror));
    d3.select("#" + "BT_ROR_SMOOTH").attr("d", lineROR(store.channels[0].ror_smoothed));
  });

  // Append the SVG element.
  document.getElementById("main_chart").append(svg.node());

  // const socket = io("http://localhost:8000", {
  //   opts: { path: "/socket.io" },
  // });
  const socket = io();

  socket.on("read_device", (channels) => {
    console.log(channels);
    store.channels = channels;
  });
}

export default App;
