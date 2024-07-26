import { createApp, ref, onMounted, reactive, watchEffect  } from 'vue'

const width = 860;
const height = 550;
const marginTop = 20;
const marginRight = 20;
const marginBottom = 30;
const marginLeft = 40;

// Declare the x (horizontal position) scale.
const xScale = d3
    .scaleLinear()
    .domain([-60, 780])
    .range([marginLeft, width - marginRight]);

// Declare the y (vertical position) scale on the left
const yScale = d3
    .scaleLinear()
    .domain([80, 380])
    .range([height - marginBottom, marginTop]);

// Declare the y (vertical position) scale on the right
const yScaleROR = d3
    .scaleLinear()
    .domain([0, 24])
    .range([height - marginBottom, marginTop]);

// Declare the line generator.
const line = d3.line()
    .x((p) => xScale(p.t))
    .y((p) => yScale(p.v));

const lineROR = d3.line()
    .x((p) => xScale(p.t))
    .y((p) => yScaleROR(p.v));


const app = createApp({
    setup() {
        
        let timer = ref("0:00");        

        let store = reactive({
            channels: settings.channels.map((c) => ({
              id: c.id,
              color: c.color,
              current_data: 0,
              current_ror: 0,
              data: [],
              ror: [],
              ror_filtered: [],
              ror_smoothed: []
            })),
            
            roast_events: {}
          });

        // let channels_nodes = [];    

        let roast_events_node;       


        onMounted(() => {    
        
            // Create the SVG container.
            const svg = d3.select("#main_chart")           
        
            svg.append("path")
                .attr("id", "BT_ROR")
                .attr("fill", "none")
                .attr("stroke", "#2E8B57")
                .attr("stroke-width", 1)
                .attr("d", lineROR(store.channels[0].ror));

            svg.append("path")
                .attr("id", "BT_ROR_SMOOTH")
                .attr("fill", "none")
                .attr("stroke", "#0000FF")
                .attr("stroke-width", 2)
                .attr("d", lineROR(store.channels[0].ror_smoothed));

            roast_events_node = svg.append("g")
            
            watchEffect(() => {
           
                d3.select("#" + "BT_ROR").attr("d", lineROR(store.channels[0].ror));
                d3.select("#" + "BT_ROR_SMOOTH").attr("d", lineROR(store.channels[0].ror_smoothed));
            });
            
        })

        // const socket = io("http://localhost:8000", {
        //   opts: { path: "/socket.io" },
        // });
        const socket = io();

        socket.on("read_device", (channels) => {
            console.log(channels);
            store.channels = channels;
        });

        socket.on('update_timer', 
            (t) => { 

                timer.value = 
                Math.floor(Math.round(t) / 60).toString() +
                        ':' +
                        (Math.round(t) % 60).toString().padStart(2, '0');
               
        });

        socket.on("roast_events", (roast_events) => {
            console.log(roast_events);
            store.roast_events = roast_events;
        
            roast_events_node.selectAll("*").remove();
        
            for (const[key, idx] of Object.entries(roast_events)) {
                if (idx != 0){
                let x = xScale(store.channels[0].data[idx].t)
                let y = yScale(store.channels[0].data[idx].v)
        
                roast_events_node.append("line")
                    .attr("stroke", "black")
                    .attr("stroke-width", 1)
                    .attr("x1", x + 2)
                    .attr("y1", y + 2)
                    .attr("x2", x + 10)
                    .attr("y2", y + 10)
        
                roast_events_node.append("circle")
                    .attr("cx", x)
                    .attr("cy", y)
                    .attr("r", 2)
                
                roast_events_node.append("text")
                    .attr("alignment-baseline", "hanging" )
                    .attr("font-size", "small" )
                    .attr("x", x + 10)
                    .attr("y", y + 10)
                    .text(key)
                }
        
            }
            
        });

        return {
            width : width,
            height : height,
            marginTop : marginTop,
            marginRight : marginRight,
            marginBottom : marginBottom,
            marginLeft : marginLeft,
            line,
            timer,
            store
        }
    }
})

// Delimiters changed to ES6 template string style
app.config.compilerOptions.delimiters = ['${', '}']

app.directive(
    'x_axis', (el, binding) => {
        d3.select(el).call(d3.axisBottom(xScale));
    }
)

app.directive(
    'y_axis', (el, binding) => {
        d3.select(el).call(d3.axisLeft(yScale));
    }
)

app.directive(
    'y_axis_ror', (el, binding) => {
        d3.select(el).call(d3.axisRight(yScaleROR));
    }
)

app.mount('#app')
