import { defineComponent, h } from "vue";

import { sanitizeHtml } from "@/lib/firewall";

export default defineComponent({
  name: "SanitizedHtml",
  inheritAttrs: false,
  props: {
    html: {
      type: String,
      required: true,
    },
    svg: {
      type: Boolean,
      default: false,
    },
    tag: {
      type: String,
      default: "div",
    },
  },
  setup(props, { attrs }) {
    return () =>
      h(props.tag, {
        ...attrs,
        innerHTML: sanitizeHtml(props.html, { svg: props.svg }),
      });
  },
});
