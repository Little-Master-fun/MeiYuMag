import * as THREE from 'three'

export interface ParchmentPageCanvas {
  texture: THREE.CanvasTexture
  updateText: (text: string) => void
  scrollBy: (delta: number) => void
  tick: () => void
}

const PAGE_WIDTH = 1024
const PAGE_HEIGHT = 1400
const CONTENT_HEIGHT = 2780
const MAX_SCROLL = CONTENT_HEIGHT - PAGE_HEIGHT

function drawSection(
  ctx: CanvasRenderingContext2D,
  index: string,
  title: string,
  body: string[],
  y: number,
) {
  ctx.fillStyle = 'rgba(93, 73, 48, 0.58)'
  ctx.font = '600 25px "Palatino Linotype", Palatino, Georgia, serif'
  ctx.textAlign = 'left'
  ctx.fillText(index, 176, y)

  ctx.fillStyle = '#5d4930'
  ctx.font = '600 46px "Songti SC", "STSong", Georgia, serif'
  ctx.fillText(title, 236, y + 4)

  ctx.strokeStyle = 'rgba(93, 73, 48, 0.2)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(176, y + 48)
  ctx.lineTo(848, y + 48)
  ctx.stroke()

  ctx.fillStyle = 'rgba(77, 60, 40, 0.78)'
  ctx.font = '30px "Songti SC", "STSong", Georgia, serif'
  body.forEach((line, lineIndex) => ctx.fillText(line, 176, y + 112 + lineIndex * 52))
}

function drawParchment(ctx: CanvasRenderingContext2D, text: string, scrollY: number) {
  ctx.clearRect(0, 0, PAGE_WIDTH, PAGE_HEIGHT)
  ctx.save()
  ctx.translate(0, -scrollY)

  const titleFont = '600 92px "Palatino Linotype", "Book Antiqua", Palatino, Georgia, serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = '#5d4930'
  ctx.shadowColor = 'rgba(77, 53, 27, 0.12)'
  ctx.shadowBlur = 2
  ctx.shadowOffsetY = 1
  ctx.font = titleFont
  ctx.fillText(text, PAGE_WIDTH / 2, 340)
  const titleWidth = Math.min(ctx.measureText(text).width + 100, 620)

  const lineY = 420
  ctx.strokeStyle = 'rgba(93, 73, 48, 0.34)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo((PAGE_WIDTH - titleWidth) / 2, lineY)
  ctx.lineTo((PAGE_WIDTH + titleWidth) / 2, lineY)
  ctx.stroke()

  ctx.fillStyle = 'rgba(93, 73, 48, 0.58)'
  ctx.save()
  ctx.translate(PAGE_WIDTH / 2, lineY)
  ctx.rotate(Math.PI / 4)
  ctx.fillRect(-5, -5, 10, 10)
  ctx.restore()

  ctx.save()
  drawSection(
    ctx,
    '01',
    '纸页中的网页',
    ['这张纸现在也是一块可以浏览的内容区域。', '将鼠标停留在纸面上，滚动即可阅读后续内容。'],
    610,
  )
  drawSection(
    ctx,
    '02',
    '活动管理',
    ['查看活动申请、处理进度与组织信息。', '内容始终贴合纸张，不会产生额外的模型厚度。'],
    1120,
  )
  drawSection(
    ctx,
    '03',
    '场地日历',
    ['浏览场地的开放时间与预约状态。', '移出纸张后，滚轮会恢复为场景镜头缩放。'],
    1630,
  )
  drawSection(
    ctx,
    '04',
    '组织认证',
    ['手机号认证成功后，再保存组织、用户名和密码。', '所有内容都可以继续替换为真实的网页数据。'],
    2140,
  )
  ctx.restore()
  ctx.restore()

  // A restrained fixed-position indicator makes the paper's scroll state clear
  // without introducing a conventional bright browser scrollbar.
  const progress = MAX_SCROLL > 0 ? scrollY / MAX_SCROLL : 0
  ctx.fillStyle = 'rgba(93, 73, 48, 0.12)'
  ctx.fillRect(PAGE_WIDTH - 72, 250, 3, 900)
  ctx.fillStyle = 'rgba(93, 73, 48, 0.48)'
  ctx.fillRect(PAGE_WIDTH - 74, 250 + progress * 820, 7, 80)
}

export function createParchmentPageCanvas(
  initialText: string,
  maxAnisotropy: number,
): ParchmentPageCanvas {
  const canvas = document.createElement('canvas')
  canvas.width = PAGE_WIDTH
  canvas.height = PAGE_HEIGHT
  const context = canvas.getContext('2d')
  if (!context) throw new Error('Canvas 2D context is unavailable')

  let text = initialText
  let currentScroll = 0
  let targetScroll = 0

  const texture = new THREE.CanvasTexture(canvas)
  texture.name = 'Parchment_Page_Content'
  texture.colorSpace = THREE.SRGBColorSpace
  texture.anisotropy = Math.min(maxAnisotropy, 8)
  texture.minFilter = THREE.LinearMipmapLinearFilter
  texture.magFilter = THREE.LinearFilter

  const updateText = (text: string) => {
    drawParchment(context, text, currentScroll)
    texture.needsUpdate = true
  }

  const scrollBy = (delta: number) => {
    targetScroll = THREE.MathUtils.clamp(targetScroll + delta, 0, MAX_SCROLL)
  }

  const tick = () => {
    const difference = targetScroll - currentScroll
    if (Math.abs(difference) < 0.1) {
      if (currentScroll !== targetScroll) {
        currentScroll = targetScroll
        drawParchment(context, text, currentScroll)
        texture.needsUpdate = true
      }
      return
    }

    currentScroll += difference * 0.14
    drawParchment(context, text, currentScroll)
    texture.needsUpdate = true
  }

  const setText = (nextText: string) => {
    text = nextText
    updateText(text)
  }

  updateText(text)
  return { texture, updateText: setText, scrollBy, tick }
}
