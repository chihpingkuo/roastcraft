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
    .x((p) => xScale(p.time))
    .y((p) => yScale(p.value));

const lineROR = d3.line()
    .x((p) => xScale(p.time))
    .y((p) => yScaleROR(p.value));


const app = createApp({
    setup() {
        
        let timer = ref("0:00");        

        let store = ref({
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
            
            roast_events: []
          });        

        // const socket = io("http://localhost:8000", {
        //   opts: { path: "/socket.io" },
        // });
        const socket = io();

        socket.on("read_device", (channels) => {
            console.log(channels);
            store.value.channels = channels;
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
            store.value.roast_events = roast_events
            
        });

        return {
            width : width,
            height : height,
            marginTop : marginTop,
            marginRight : marginRight,
            marginBottom : marginBottom,
            marginLeft : marginLeft,
            xScale,
            yScale,
            line,
            lineROR,
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
