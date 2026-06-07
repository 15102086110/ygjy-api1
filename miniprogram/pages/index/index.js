// pages/index/index.js
const api = require('../../utils/api.js')

Page({
  data: {
    activeTab: 'today',
    yearFilter: 'all',
    projects: [],
    loading: true,
    keyword: '',
    stats: { today: 0, week: 0, month: 0, year: 0 }
  },

  onLoad() {
    this.loadData()
  },

  onPullDownRefresh() {
    this.loadData(() => {
      wx.stopPullDownRefresh()
    })
  },

  onTabTap(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab })
  },

  onYearTap(e) {
    const year = e.currentTarget.dataset.year
    this.setData({ yearFilter: year, projects: [] })
    this.loadData()
  },

  loadData(callback) {
    this.setData({ loading: true })
    
    const params = { pageSize: 200 }
    if (this.data.yearFilter !== 'all') {
      params.year = this.data.yearFilter
    }
    if (this.data.keyword) {
      params.keyword = this.data.keyword
    }
    
    // 加载楼盘列表
    const projectsPromise = api.request('/api/projects', params).then(res => {
      const rawData = res.data || res || []
      const projects = rawData.map((p, index) => {
        const presell = String(p.presell || '')
        const yearStr = presell.substring(0, 4)
        const year = /^\d{4}$/.test(yearStr) ? parseInt(yearStr) : null
        
        return {
          id: p.projectId || p.projectID || String(index),
          projectName: p.projectName || '未知楼盘',
          developer: p.developer || '未知开发商',
          houseSoldNum: parseInt(p.houseSoldNum) || 0,
          houseUnsaleNum: parseInt(p.houseUnsaleNum) || 0,
          presell: presell,
          year: year,
          address: p.projectAddress || ''
        }
      })
      return projects.sort((a, b) => b.houseSoldNum - a.houseSoldNum)
    })

    // 加载今日签约数据
    const signingPromise = api.request('/api/signing/daily', { page: 1, pageSize: 50 }).then(res => {
      return res.todaySignedCount || 0
    }).catch(() => {
      return 0
    })

    // 并行请求
    Promise.all([projectsPromise, signingPromise]).then(([sorted, todaySigned]) => {
      this.setData({
        projects: sorted,
        loading: false,
        stats: {
          today: todaySigned,
          week: -1,     // coming soon
          month: -1,    // coming soon
          year: -1      // coming soon
        }
      })
      if (callback) callback()
    }).catch(err => {
      console.error('加载失败:', err)
      this.setData({ loading: false })
      if (callback) callback()
    })
  },

  onInput(e) {
    this.setData({ keyword: e.detail.value })
  },

  onSearch() {
    this.setData({ projects: [] })
    this.loadData()
  },

  onTap(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: '/pages/detail/detail?id=' + id })
  }
})