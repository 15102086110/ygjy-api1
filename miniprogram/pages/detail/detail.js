// pages/detail/detail.js
const api = require('../../utils/api.js')

Page({
  data: {
    project: null,
    buildings: [],
    loading: true,
    sellRate: { percent: 0, total: 0 }
  },

  onLoad(options) {
    this.projectId = options.id
    this.loadDetail()
    this.loadBuildings()
  },

  loadDetail() {
    api.request('/api/projects/' + this.projectId).then(data => {
      // 处理数据格式
      const p = data || {}
      const sold = parseInt(p.houseSoldNum) || 0
      const unsale = parseInt(p.houseUnsaleNum) || 0
      const total = sold + unsale
      const percent = total > 0 ? Math.round(sold / total * 100) : 0
      
      this.setData({ 
        project: {
          id: p.projectId || this.projectId,
          projectName: p.projectName || '未知楼盘',
          developer: p.developer || '未知开发商',
          houseSoldNum: sold,
          houseUnsaleNum: unsale,
          presell: p.presell || null,
          address: p.projectAddress || ''
        },
        sellRate: { percent, total }
      })
    }).catch(err => {
      wx.showToast({ title: '加载失败', icon: 'none' })
    })
  },

  loadBuildings() {
    api.request('/api/projects/' + this.projectId + '/buildings').then(data => {
      const buildings = (data.data || data || []).map(b => ({
        buildingId: b.buildingId || b.buildingID || b.id,
        buildingName: b.buildingName || '楼栋'
      }))
      this.setData({
        buildings,
        loading: false
      })
    }).catch(err => {
      this.setData({ loading: false })
    })
  },

  onBuildingTap(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: '/pages/building/building?id=' + id })
  }
})